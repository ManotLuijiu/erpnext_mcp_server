import { useQuery } from '@tanstack/react-query';

export interface UseRunningStatusProps {
  environmentId?: string;
}

export function useRunningStatus({ environmentId }: UseRunningStatusProps) {
  return useQuery({
    enabled: Boolean(environmentId),
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    staleTime: Number.POSITIVE_INFINITY,
  });
}
