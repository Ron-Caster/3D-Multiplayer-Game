from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import json
import secrets
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store connected players and their positions, health, and nicknames
players = {}

# Constants
PLAYER_START_Y = 1.8  # Starting height for players
MAP_HALF_SIZE = 45  # Map boundaries, matching the React version

# Define obstacles in the game world
OBSTACLES = [
    {'x': 10, 'y': 2.5, 'z': 10, 'width': 5, 'height': 5, 'depth': 5},
    {'x': -15, 'y': 1.5, 'z': -15, 'width': 4, 'height': 3, 'depth': 4}
]

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    # Initialize new player position and properties in 3D space
    players[request.sid] = {
        'x': random.uniform(-MAP_HALF_SIZE/2, MAP_HALF_SIZE/2),  # random x position
        'y': PLAYER_START_Y,  # starting height
        'z': random.uniform(-MAP_HALF_SIZE/2, MAP_HALF_SIZE/2),  # random z position
        'rotY': 0,  # horizontal rotation
        'health': 100,  # starting health
        'nickname': '',  # will be set later
        'color': 0x00ff00  # default color (green)
    }
    # Send initial state to new player including obstacles
    emit('init', {
        'id': request.sid, 
        'players': players,
        'obstacles': OBSTACLES
    })

@socketio.on('set-nickname')
def handle_nickname(data):
    if request.sid in players:
        players[request.sid]['nickname'] = data['nickname']
        # Broadcast new player to others
        emit('new-player', {'id': request.sid, 'data': players[request.sid]}, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in players:
        del players[request.sid]
        emit('remove-player', request.sid, broadcast=True)

@socketio.on('move')
def handle_move(data):
    if request.sid in players:
        # Update position and rotation
        players[request.sid]['x'] = data['x']
        players[request.sid]['y'] = data['y']
        players[request.sid]['z'] = data['z']
        players[request.sid]['rotY'] = data['rotY']
        # Broadcast update to others
        emit('update-player', {'id': request.sid, 'data': players[request.sid]}, broadcast=True, include_self=False)

@socketio.on('shoot')
def handle_shoot(data):
    if request.sid in players and 'hitPlayerId' in data:
        hit_player_id = data['hitPlayerId']
        if hit_player_id in players:
            # Reduce health of hit player
            players[hit_player_id]['health'] -= 20  # Damage per hit
            if players[hit_player_id]['health'] <= 0:
                # Player is eliminated
                del players[hit_player_id]
                emit('remove-player', hit_player_id, broadcast=True)
            else:
                # Update hit player's state
                emit('update-player', {'id': hit_player_id, 'data': players[hit_player_id]}, broadcast=True)
            
            # Notify about the shot
            emit('player-fired', {'shooterId': request.sid}, broadcast=True)

if __name__ == '__main__':
    print("You can connect using any of these URLs:")
    print("http://192.168.29.90:8080")
    print("http://192.168.137.1:8080")
    socketio.run(app, host='0.0.0.0', port=8080)
