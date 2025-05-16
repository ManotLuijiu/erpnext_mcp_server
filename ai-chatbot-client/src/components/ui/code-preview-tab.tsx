'use client';

import * as React from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const CodePreviewTab = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Root>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Root ref={ref} className={cn('w-fit', className)} {...props} />
));
CodePreviewTab.displayName = TabsPrimitive.Root.displayName;

const CodePreviewTabList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, children, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn('inline-flex h-10 items-center', className)}
    {...props}
  >
    {children}
  </TabsPrimitive.List>
));
CodePreviewTabList.displayName = TabsPrimitive.List.displayName;

const CodePreviewTabTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, children, ...props }, ref) => {
  // Track if tab is active for animation
  const [isActive, setIsActive] = React.useState(false);
  const triggerRef = React.useRef<HTMLButtonElement | null>(null);

  // Setup a callback ref to handle both refs
  const setRefs = React.useCallback(
    (node: HTMLButtonElement | null) => {
      // Set our internal ref
      triggerRef.current = node;

      // Handle the forwarded ref
      if (typeof ref === 'function') {
        ref(node);
      } else if (ref) {
        (ref as React.MutableRefObject<HTMLButtonElement | null>).current =
          node;
      }
    },
    [ref]
  );

  React.useEffect(() => {
    const element = triggerRef.current;
    if (!element) return;

    // Function to check active state
    const checkActive = () => {
      const isActiveNow = element.getAttribute('data-state') === 'active';
      setIsActive(isActiveNow);
    };

    // Run immediately
    checkActive();

    // Create observer to watch for attribute changes
    const observer = new MutationObserver(checkActive);
    observer.observe(element, { attributes: true });

    return () => observer.disconnect();
  }, []);

  return (
    <TabsPrimitive.Trigger
      ref={setRefs}
      className={cn(
        'relative px-5 h-10 flex items-center justify-center',
        'text-[#8a8a8d] data-[state=active]:text-white',
        'text-sm font-medium tracking-wide',
        'transition-colors duration-200',
        'focus:outline-none focus-visible:bg-white/5',
        'select-none group',
        className
      )}
      {...props}
    >
      <span className="relative z-10">{children}</span>

      {/* Subtle background indicator only visible on hover when not active */}
      <span
        className={cn(
          'absolute inset-0 rounded-sm bg-white/5 opacity-0 transition-opacity group-hover:opacity-100',
          isActive ? 'hidden' : ''
        )}
      />

      {/* Active indicator line */}
      {isActive && (
        <motion.div
          layoutId="activeTabLine"
          className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#3b82f6]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
        />
      )}
    </TabsPrimitive.Trigger>
  );
});
CodePreviewTabTrigger.displayName = TabsPrimitive.Trigger.displayName;

const CodePreviewTabContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      'outline-none w-full h-full transition-all',
      'data-[state=inactive]:opacity-0 data-[state=active]:opacity-100',
      'data-[state=inactive]:translate-y-1 data-[state=active]:translate-y-0',
      'data-[state=inactive]:pointer-events-none',
      'duration-200 ease-in-out',
      className
    )}
    {...props}
  />
));
CodePreviewTabContent.displayName = TabsPrimitive.Content.displayName;

export {
  CodePreviewTab,
  CodePreviewTabList,
  CodePreviewTabTrigger,
  CodePreviewTabContent,
};
