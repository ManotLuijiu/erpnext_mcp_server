function chat_app_handlers(socket) {
  socket.on('hello_chat', (data) => {
    console.log('Received hello_chat:', data);
    socket.emit('hello_chat_response', { message: 'Acknowledged' });
  });
}

module.exports = chat_app_handlers;
