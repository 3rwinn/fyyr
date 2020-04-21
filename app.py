#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import load_only
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
import time, datetime, sys
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Show(db.Model):
  __tablename__= 'show'

  artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), primary_key=True)
  venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), primary_key=True)
  start_time = db.Column(db.String())
  artist = db.relationship("Artist", back_populates="venues")
  venue = db.relationship("Venue", back_populates="artist")

class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False, nullable=False)
    seeking_description = db.Column(db.Text, nullable=True)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(100), nullable=True)
    artist = db.relationship("Show", back_populates="venue")

class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120), nullable=False)
    website = db.Column(db.String(100))
    seeking_venue = db.Column(db.Boolean, default=False, nullable=False)
    seeking_description = db.Column(db.Text, nullable=True)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    venues = db.relationship("Show", back_populates="artist")

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  cities = Venue.query.distinct('city')
  
  areas = []
  for c in cities:
    data = {}
    data["city"] = c.city
    data["state"] = c.state
    data["venues"] = Venue.query.filter_by(city = c.city).options(load_only("id", "name"))
    data["num_upcoming_shows"] = Show.query.filter_by(venue_id = c.id).count()
    areas.append(data)

  return render_template('pages/venues.html', areas=areas)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '')
  look_for = '%{0}%'.format(search_term)
  venues = Venue.query.filter(Venue.name.ilike(look_for))
  venue_count = Venue.query.filter(Venue.name.ilike(look_for)).count()
  response= {
    "count": 0,
    "data": []
  }
  for venue in venues:
    current_venue = {}
    current_venue = {
      "id": venue.id,
      "name": venue.name,
      "num_upcoming_shows": Show.query.filter_by(venue_id = venue.id).count()
    }
    response["count"] = venue_count
    response["data"].append(current_venue)

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue = Venue.query.get(venue_id)
  shows = Show.query.filter_by(venue_id=venue.id).join(Artist).all()

  data = {
    "id": venue.id,
    "name": venue.name,
    "address": venue.address,
    "city": venue.city,
    "genres": venue.genres,
    "phone": venue.phone,
    "website": venue.website_link,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": [],
    "upcoming_shows": [],
    "past_shows_count": 0,
    "upcoming_shows_count": 0
  }

  for show in shows:
    current_show = {}
    current_show["artist_id"] = show.artist_id
    current_show["artist_name"] = show.artist.name
    current_show["artist_image_link"] = show.artist.image_link
    current_show["start_time"] = show.start_time

    # Get show start_time and convert it to timestamp and compare it with 
    # current timestamp to see if it's an upcoming or past show
    datestring = show.start_time
    formated = datetime.datetime.strptime(datestring, '%Y-%m-%d %H:%M:%S')
    timestamp = datetime.datetime.timestamp(formated) 
    current_timestamp = time.time()
    
    if(current_timestamp > timestamp):
      data["past_shows"].append(current_show)
      data["past_shows_count"] += 1
    else:
      data["upcoming_shows"].append(current_show)
      data["upcoming_shows_count"] += 1

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    phone = request.form['phone']
    genres = request.form['genres']

    if(request.form['seeking_talent'] == 'True'):
      seeking_talent = True
    else:
      seeking_talent = False
    
    seeking_description = request.form['seeking_description']
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    website_link = request.form['website_link']

    newvenue = Venue(name=name, city=city, state=state, address=address, genres=genres, phone=phone, seeking_talent=seeking_talent, seeking_description=seeking_description, image_link=image_link, facebook_link=facebook_link, website_link=website_link)
    db.session.add(newvenue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    # on successful db insert, flash success
    flash('Venue ' + request.form["name"] + ' was successfully listed!')
  else:
    flash('An error occurred. Venue ' + request.form["name"] + ' could not be listed.')
    abort(500)
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  error = False
  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    abort(404)
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.options(load_only('id', 'name'))

  return render_template('pages/artists.html', artists=artists)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  look_for = '%{0}%'.format(search_term)
  artists = Artist.query.filter(Artist.name.ilike(look_for))
  artist_count = Artist.query.filter(Artist.name.ilike(look_for)).count()
  response= {
    "count": 0,
    "data": []
  }
  for artist in artists:
    current_artist = {}
    current_artist = {
      "id": artist.id,
      "name":  artist.name,
      "num_upcoming_shows": Show.query.filter_by(artist_id =  artist.id).count()
    }
    response["count"] = artist_count
    response["data"].append(current_artist)

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  artist = Artist.query.get(artist_id)
  shows = Show.query.filter_by(artist_id=artist.id).join(Venue).all()

  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": [],
    "upcoming_shows": [],
    "past_shows_count": 0,
    "upcoming_shows_count": 0
  }

  for show in shows:
    current_show = {}
    current_show["venue_id"] = show.venue_id
    current_show["venue_name"] = show.venue.name
    current_show["venue_image_link"] = show.venue.image_link
    current_show["start_time"] = show.start_time

    # Get show start_time and convert it to timestamp and compare it with 
    # current timestamp to see if it's an upcoming or past show
    datestring = show.start_time
    formated = datetime.datetime.strptime(datestring, '%Y-%m-%d %H:%M:%S')
    timestamp = datetime.datetime.timestamp(formated) 
    current_timestamp = time.time()
    
    if(current_timestamp > timestamp):
      data["past_shows"].append(current_show)
      data["past_shows_count"] += 1
    else:
      data["upcoming_shows"].append(current_show)
      data["upcoming_shows_count"] += 1
  
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.get(artist_id)

  form.name.data = artist.name 
  form.genres.data = artist.genres 
  form.city.data = artist.city 
  form.state.data = artist.state 
  form.phone.data = artist.phone
  form.facebook_link.data = artist.facebook_link

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  error = False
  try:
    artist = Artist.query.get(artist_id)
    artist.name = request.form['name']
    artist.genres = request.form['genres']
    artist.city = request.form['city']
    artist.state = request.form['state']
    artist.phone = request.form['phone']
    artist.facebook_link = request.form['facebook_link']
    
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    flash("Artist " + request.form["name"] + " updated successfully")
  else:
    flash("An error occured")
    abort(404)
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  form.name.data = venue.name
  form.address.data = venue.address
  form.genres.data = venue.genres
  form.city.data = venue.city
  form.state.data = venue.state
  form.phone.data = venue.phone
  form.facebook_link.data = venue.facebook_link

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  error = False
  try:
    venue = Venue.query.get(venue_id)
    venue.name = request.form["name"]
    venue.address = request.form["address"]
    venue.genres = request.form["genres"]
    venue.city = request.form["city"]
    venue.state = request.form["state"]
    venue.phone = request.form["phone"]
    venue.facebook_link = request.form["facebook_link"]

    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    flash("Venue " + request.form["name"] + " updated successfully")
  else:
    flash("An error occured")
    abort(404)
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  error = False
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    
    # Since ArtistForm return Boolean value in string
    # we do a condition on it to set the correct value for seeking_venue
    if(request.form['seeking_venue'] == 'True'):
      seeking_venue = True
    else:
      seeking_venue = False
    
    seeking_description = request.form['seeking_description']
    image_link = request.form['image_link']
    genres = request.form['genres']
    facebook_link = request.form['facebook_link']

    newartist = Artist(name=name, city=city, state=state, phone=phone, image_link=image_link, genres=genres, facebook_link=facebook_link, seeking_venue=seeking_venue, seeking_description=seeking_description)
    db.session.add(newartist)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())

  finally:
    db.session.close()
  if not error:
    # on successful db insert, flash success
    flash('Artist ' + request.form["name"] + ' was successfully listed!')
  else:
    flash('An error occured. Artist ' + request.form["name"] + ' could not be listed.')
    abort(500)
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  shows = Show.query.join(Artist, Venue).all()
  data = []

  for sh in shows:
    show = {}
    show["venue_id"] = sh.venue_id
    show["venue_name"] = sh.venue.name
    show["artist_id"] = sh.artist_id
    show["artist_name"] = sh.artist.name
    show["artist_image_link"] = sh.artist.image_link
    show["start_time"] = sh.start_time
    data.append(show)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  error = False
  try:
    artist_id = request.form["artist_id"]
    venue_id = request.form["venue_id"]
    start_time = request.form["start_time"]

    newshow = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
    db.session.add(newshow)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()
  if not error:
    # on successful db insert, flash success
    flash('Show was successfully listed!')
  else:
    flash('An error occurred. Show could not be listed.')
    abort(500)
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
