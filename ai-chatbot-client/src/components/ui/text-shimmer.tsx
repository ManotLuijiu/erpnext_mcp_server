'use client';
import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ShimmerTextProps {
  children: React.ReactNode;
  as?: React.ElementType;
  className?: string;
}

const ShimmerText = ({ children, className }: ShimmerTextProps) => {
  const spread = 20;

  return (
    <motion.span
      className={cn(
        'text-transparent bg-clip-text relative inline-block',
        className
      )}
      initial={{ backgroundPosition: '100% center' }}
      animate={{ backgroundPosition: '0% center' }}
      transition={{
        repeat: Infinity,
        duration: 2,
        ease: 'linear',
        repeatType: 'loop',
      }}
      style={{
        backgroundImage: `linear-gradient(90deg, rgba(0,0,0,0) calc(50% - ${spread}px), #fefefe, rgba(0,0,0,0) calc(50% + ${spread}px)), linear-gradient(#969798, #969798)`,
        backgroundSize: '250% 100%, 100% 100%',
        backgroundRepeat: 'no-repeat, no-repeat',
      }}
    >
      {children}
    </motion.span>
  );
};

export { ShimmerText };
