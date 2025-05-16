function custom_handlers(socket) {
  socket.on('custom_event', (data) => {
    console.log('Received custom_event:', data);
    socket.emit('custom_response', { message: 'Acknowledged' });
  });
}

module.exports = custom_handlers;
