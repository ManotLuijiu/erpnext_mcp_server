import { FitAddon } from '@xterm/addon-fit'
import { useEffect } from 'react'
import { useXTerm } from 'react-xtermjs'

const TerminalComponent = () => {
  const { instance, ref } = useXTerm()
  const fitAddon = new FitAddon()

  useEffect(() => {
    // Load the fit addon
    instance?.loadAddon(fitAddon)

    const handleResize = () => fitAddon.fit()

    // Write custom message on your terminal
    instance?.writeln('Welcome react-xtermjs!')
    instance?.writeln('This is a simple example using an addon.')

    // Handle resize event
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [ref, instance])

  return <div ref={ref} style={{ height: '100%', width: '100%' }} />
}