import { Badge, Flex, Separator, Text } from '@radix-ui/themes';
import { usePageStore } from '../stores/pageStore';
import { useProjectStore } from '../stores/projectStore';

export function StatusBar() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const { currentPage, pages, viewerInfo, cursorPos, zoomLevel } = usePageStore();

  const currentIndex = currentPage ? pages.findIndex((p) => p.id === currentPage.id) + 1 : 0;

  return (
    <Flex
      align="center"
      justify="between"
      px="3"
      py="1.5"
      className="border-t border-gray-800 bg-gray-950 text-xs text-gray-400 select-none font-mono"
    >
      {/* Left: Project & Page Status */}
      <Flex align="center" gap="3">
        {currentProject ? (
          <Text size="1" className="text-gray-300">
            Project: <strong className="text-white">{currentProject.name}</strong>
          </Text>
        ) : (
          <Text size="1" color="gray">
            No active project
          </Text>
        )}

        {currentPage && (
          <>
            <Separator orientation="vertical" />
            <Text size="1">
              Page: {currentIndex} / {pages.length} ({currentPage.filename})
            </Text>
            <Badge color="green" size="1">
              {currentPage.status}
            </Badge>
          </>
        )}
      </Flex>

      {/* Right: Resolution, Zoom & Live Master Pixel Coordinates */}
      <Flex align="center" gap="3">
        {viewerInfo && (
          <>
            <Text size="1" className="text-gray-300">
              Master: {viewerInfo.master_width} × {viewerInfo.master_height} px
            </Text>
            <Separator orientation="vertical" />
            <Text size="1" className="text-gray-300">
              {viewerInfo.dpi} DPI
            </Text>
            <Separator orientation="vertical" />
          </>
        )}

        <Text size="1" className="text-blue-400 font-bold min-w-[60px]">
          Zoom: {Math.round(zoomLevel * 100)}%
        </Text>

        <Separator orientation="vertical" />

        <Text size="1" className="text-emerald-400 font-bold min-w-[130px]">
          {cursorPos ? `X: ${cursorPos.x}, Y: ${cursorPos.y}` : 'X: —, Y: —'}
        </Text>
      </Flex>
    </Flex>
  );
}
