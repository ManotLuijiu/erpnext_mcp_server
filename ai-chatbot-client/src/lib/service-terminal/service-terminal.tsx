import type { QueryClient } from '@tanstack/react-query';
import { AttachAddon } from '@xterm/addon-attach';
import { FitAddon } from '@xterm/addon-fit';
import type { ITerminalAddon } from '@xterm/xterm';
import {
  memo,
  useCallback,
  useContext,
  useState,
  type MouseEvent as MouseDownEvent,
} from 'react';
import { createPortal } from 'react-dom';
import { XTerm } from 'react-xtermjs';
import { Button } from '@/components/ui/button';
import { Icon, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { InputSearch } from './input-search/input-search';
import { ServiceTerminalContext } from './service_terminal-provider';

const MemoizedXTerm = memo(XTerm);

export interface ServiceTerminalProps {
  organizationId: string;
  clusterId: string;
  projectId: string;
  environmentId: string;
  serviceId: string;
}

export function ServiceTerminal({
  organizationId,
  clusterId,
  projectId,
  environmentId,
  serviceId,
}: ServiceTerminalProps) {
  const { setOpen } = useContext(ServiceTerminalContext);
  const MIN_TERMINAL_HEIGHT = 248;
  const MAX_TERMINAL_HEIGHT = document.body.clientHeight - 64 - 60; // 64 (navbar) + 60 (terminal header)
  const [terminalParentHeight, setTerminalParentHeight] =
    useState(MIN_TERMINAL_HEIGHT);
  const [addons, setAddons] = useState<Array<ITerminalAddon>>([]);
  const isTerminalLoading = addons.length < 2;
  const fitAddon = addons[0] as FitAddon | undefined;

  const [selectedPod, setSelectedPod] = useState<string | undefined>();
  const [selectedContainer, setSelectedContainer] = useState<
    string | undefined
  >();

  const onOpenHandler = useCallback(
    (_: QueryClient, event: Event) => {
      const websocket = event.target as WebSocket;
      const fitAddon = new FitAddon();
      // As WS are open twice in dev mode / strict mode it doesn't happens in production
      setAddons([fitAddon, new AttachAddon(websocket)]);
    },
    [setAddons]
  );

  const onCloseHandler = useCallback(
    (_: QueryClient, event: CloseEvent) => {
      if (event.code !== 1006 && event.reason) {
        toast('ERROR', 'Not available', event.reason);
        setOpen(false);
      }
    },
    [setOpen]
  );

  // Necesssary to calculate the number of rows and columns (tty) for the terminal
  // https://github.com/xtermjs/xterm.js/issues/1412#issuecomment-724421101
  // 16 is the font height
  const rows = Math.ceil(document.body.clientHeight / 16);
  const cols = Math.ceil(document.body.clientWidth / 8);

  useReactQueryWsSubscription({});
}
