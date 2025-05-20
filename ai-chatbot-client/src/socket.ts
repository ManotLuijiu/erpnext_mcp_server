import { io } from 'socket.io-client';
import { socketio_port } from '../../../../sites/common_site_config.json';
// import { getCachedListResource } from 'frappe-ui/src/resources/listResource';
// import { getCachedResource } from 'frappe-ui/src/resources/resources';

declare global {
  interface Window {
    site_name: string;
  }
}

export function initSocket() {
  const host = window.location.hostname;
  // const siteName = window.site_name;
  const siteName = window.frappe?.boot?.site_name || '';
  const port = window.location.port ? `:${socketio_port}` : '';
  const protocol = port ? 'http' : 'https';
  // const url = `${protocol}://${host}${port}/${siteName}`;
  // const url = `${protocol}://${host}${port}`;
  // const url = `${protocol}://${host}${port ? `:${port}` : ''}`;
  const url = 'http://localhost:9000/socket.io';

  console.log('host socket.js', host);
  console.log('siteName socket.js', siteName);
  console.log('port socket.js', port);
  console.log('protocol socket.js', protocol);
  console.log('url socket.js', url);

  const socket = io(url, {
    withCredentials: true,
    reconnectionAttempts: 5,
    path: `/${siteName}/socket.io`,
    query: {
      terminal: true,
    },
    transports: ['websocket', 'polling'],
    timeout: 20000,
    upgrade: true,
    rememberUpgrade: true,
    forceNew: true,
  });

  socket.on('connect', () => {
    console.log('Terminal socket connected');
  });

  socket.on('connect_error', (error) => {
    console.error('Terminal socket connection error: ', error);
  });

  socket.on('reconnect_attempt', (attemptNumber) => {
    console.log(`Terminal socket reconnect attempt ${attemptNumber}`);
  });

  // socket.on('refetch_resource', (data) => {
  //   console.log('data socket.js', data);
  //   if (data.cache_key) {
  //     const resource =
  //       getCachedResource(data.cache_key) ||
  //       getCachedListResource(data.cache_key);
  //     if (resource) {
  //       resource.reload();
  //     }
  //   }
  // });

  console.log('socket socket.js', socket);
  return socket;
}
