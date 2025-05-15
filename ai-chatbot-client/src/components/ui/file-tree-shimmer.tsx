import { Folder } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export function FileTreeShimmer() {
  // Predefined structure for Next.js project
  const structure = [
    // First folder group (app folder)
    { type: 'folder', name: 'app', width: '60%', indent: 0 },
    { type: 'shimmer', width: '40%', indent: 1 },
    { type: 'shimmer', width: '50%', indent: 1 },
    { type: 'shimmer', width: '45%', indent: 1 },

    // Second folder group (components)
    { type: 'folder', name: 'components', width: '75%', indent: 0 },
    { type: 'shimmer', width: '60%', indent: 1 },
    { type: 'shimmer', width: '50%', indent: 1 },
    { type: 'shimmer', width: '55%', indent: 1 },
    { type: 'shimmer', width: '45%', indent: 1 },

    // Third folder group (lib/utils)
    { type: 'folder', name: 'lib', width: '75%', indent: 0 },
    { type: 'shimmer', width: '55%', indent: 1 },
    { type: 'shimmer', width: '65%', indent: 1 },
    // Root files
    { type: 'shimmer', width: '85%', indent: 0 },
    { type: 'shimmer', width: '85%', indent: 0 },
  ];

  return (
    <div className="space-y-2 pt-1 px-2">
      {structure.map((item, index) => (
        <div
          key={index}
          className="flex items-center gap-1.5 py-1"
          style={{ paddingLeft: `${item.indent * 12}px` }}
        >
          {item.type === 'folder' && (
            <Folder className="w-3.5 h-3.5 text-[#525253]" />
          )}
          <ShimmerItem width={item.width} />
        </div>
      ))}
    </div>
  );
}

// Shimmer line item
const ShimmerItem = ({ width = '100%' }: { width?: string }) => (
  <motion.div
    className="h-3 rounded-md"
    style={{
      width,
      background:
        'linear-gradient(90deg, #1A1A1A 0%, #252525 50%, #1A1A1A 100%)',
      backgroundSize: '200% 100%',
    }}
    initial={{ backgroundPosition: '200% 0' }}
    animate={{ backgroundPosition: '-200% 0' }}
    transition={{
      duration: 2,
      repeat: Infinity,
      ease: 'linear',
    }}
  />
);
