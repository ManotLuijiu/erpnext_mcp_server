function mcp_terminal_handlers(socket) {
  socket.on('mcp_terminal_input', function (data) {
    // Forward the event to the Python backend via Redis
    socket.publish_doctype('events', {
      event: 'mcp_terminal_input',
      message: data,
      room: 'user:' + socket.user,
    });
  });
}

module.exports = mcp_terminal_handlers;
