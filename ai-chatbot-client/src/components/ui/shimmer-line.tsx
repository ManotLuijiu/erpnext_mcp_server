import { motion } from 'framer-motion';

export const ShimmerLine = ({ width = '100%' }: { width?: string }) => (
  <motion.div
    className="h-4 rounded"
    style={{
      width,
      background:
        'linear-gradient(90deg, #1E1E1E 0%, #2D2D2D 50%, #1E1E1E 100%)',
      backgroundSize: '200% 100%',
    }}
    initial={{ backgroundPosition: '200% 0' }}
    animate={{ backgroundPosition: '-200% 0' }}
    transition={{
      duration: 4,
      repeat: Infinity,
      ease: 'linear',
    }}
  />
);
