import { ReactNode } from 'react';

interface LayoutProps {
  sidebar: ReactNode;
  viewer: ReactNode;
  panel: ReactNode;
}

export function Layout({ sidebar, viewer, panel }: LayoutProps) {
  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar Panel */}
      <div className="w-72 border-r border-gray-700 bg-gray-900 flex-shrink-0">{sidebar}</div>

      {/* Viewer Panel */}
      <div className="flex-1 relative bg-black">{viewer}</div>

      {/* Region Details Panel */}
      <div className="w-80 border-l border-gray-700 bg-gray-900 flex-shrink-0">{panel}</div>
    </div>
  );
}
