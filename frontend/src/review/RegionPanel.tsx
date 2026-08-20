import { useState } from 'react';
import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  IconButton,
  ScrollArea,
  Separator,
  Slider,
  Switch,
  Text,
  TextField,
} from '@radix-ui/themes';
import {
  CheckIcon,
  CopyIcon,
  CropIcon,
  Cross2Icon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MagicWandIcon,
  TrashIcon,
} from '@radix-ui/react-icons';
import { useAnnotationStore } from '../stores/annotationStore';
import { usePageStore } from '../stores/pageStore';
import { computeBoundingBox } from '../annotation/geometryAdapter';
import { RegionStatus } from '../types/region';
import { VectorPreviewDialog } from '../components/VectorPreviewDialog';

function getStatusBadge(status: RegionStatus) {
  switch (status) {
    case 'APPROVED':
      return (
        <Badge color="green" size="1">
          APPROVED
        </Badge>
      );
    case 'REJECTED':
      return (
        <Badge color="red" size="1">
          REJECTED
        </Badge>
      );
    case 'EDITED':
      return (
        <Badge color="blue" size="1">
          EDITED
        </Badge>
      );
    case 'AUTO':
      return (
        <Badge color="amber" size="1">
          AUTO
        </Badge>
      );
  }
}

export function RegionPanel() {
  const currentPage = usePageStore((s) => s.currentPage);
  const [vectorModalOpen, setVectorModalOpen] = useState(false);
  const {
    regions,
    selectedRegionId,
    setSelectedRegionId,
    updateRegionAngle,
    updateRegionPadding,
    updateRegionExport,
    updateRegionStatus,
    deleteRegion,
    duplicateRegion,
    fitSelectedRegion,
    isFitting,
    saveStatus,
  } = useAnnotationStore();

  const selectedRegion = regions.find((r) => r.id === selectedRegionId);
  const selectedIndex = regions.findIndex((r) => r.id === selectedRegionId);

  if (!selectedRegion) {
    return (
      <Box className="h-full flex flex-col bg-gray-900 border-l border-gray-800 p-4 select-none">
        <Heading size="3" mb="2" className="text-gray-200">
          Region Inspector
        </Heading>
        <Text size="1" color="gray" mb="4">
          Select a region on the canvas or draw a new one.
        </Text>

        <div className="flex-1 flex flex-col items-center justify-center text-gray-500 text-center p-4 border border-dashed border-gray-800 rounded">
          <div className="text-3xl mb-2">🎯</div>
          <Text size="2" weight="medium">
            No Region Selected
          </Text>
          <Text size="1" color="gray" mt="1">
            {regions.length > 0
              ? `${regions.length} region(s) on this page`
              : 'Press R (Rect), O (Rotated), P (Poly), or L (Lasso)'}
          </Text>
        </div>
      </Box>
    );
  }

  const isRotated = selectedRegion.geometry.type === 'rotated_rectangle';
  const currentAngle =
    selectedRegion.geometry.type === 'rotated_rectangle' ? selectedRegion.geometry.angle : 0;
  const bounds = computeBoundingBox(selectedRegion.geometry);

  const handlePaddingChange = (side: 'top' | 'right' | 'bottom' | 'left', val: string) => {
    const num = parseInt(val, 10);
    if (!isNaN(num)) {
      updateRegionPadding(selectedRegion.id, { [side]: Math.max(0, num) });
    }
  };

  const applyPresetPadding = (px: number) => {
    updateRegionPadding(selectedRegion.id, {
      top: px,
      right: px,
      bottom: px,
      left: px,
    });
  };

  const navigateRegion = (delta: number) => {
    const nextIdx = selectedIndex + delta;
    if (nextIdx >= 0 && nextIdx < regions.length) {
      setSelectedRegionId(regions[nextIdx].id);
    }
  };

  return (
    <Box className="h-full flex flex-col bg-gray-900 border-l border-gray-800 select-none">
      {/* Header */}
      <Box p="3" className="border-b border-gray-800">
        <Flex justify="between" align="center" mb="1">
          <Flex align="center" gap="2">
            <Heading size="3" className="text-gray-100">
              Region #{selectedRegion.sequence}
            </Heading>
            {getStatusBadge(selectedRegion.status)}
          </Flex>

          <Flex align="center" gap="1">
            <IconButton
              size="1"
              variant="ghost"
              disabled={selectedIndex <= 0}
              onClick={() => navigateRegion(-1)}
            >
              <ChevronLeftIcon />
            </IconButton>
            <Text size="1" color="gray" className="font-mono">
              {selectedIndex + 1}/{regions.length}
            </Text>
            <IconButton
              size="1"
              variant="ghost"
              disabled={selectedIndex >= regions.length - 1}
              onClick={() => navigateRegion(1)}
            >
              <ChevronRightIcon />
            </IconButton>
          </Flex>
        </Flex>

        <Text size="1" color="gray" className="font-mono text-[11px]">
          ID: {selectedRegion.id} • Type: {selectedRegion.geometry.type}
        </Text>
      </Box>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {/* Fit to Content & Duplicate Actions */}
          <Flex gap="2">
            <Button
              size="1"
              color="indigo"
              variant="soft"
              className="flex-1"
              disabled={isFitting}
              onClick={fitSelectedRegion}
            >
              <CropIcon /> {isFitting ? 'Fitting...' : 'Fit to Content (F)'}
            </Button>
            <Button
              size="1"
              color="gray"
              variant="soft"
              onClick={() => duplicateRegion(selectedRegion.id)}
            >
              <CopyIcon /> Duplicate
            </Button>
          </Flex>

          {/* Coordinates (Master Pixels) */}
          <Box className="bg-gray-950/60 p-2.5 rounded border border-gray-800">
            <Text size="1" weight="bold" color="gray" mb="2" as="div">
              MASTER PIXEL BOUNDS
            </Text>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div>
                <span className="text-gray-500">X:</span>{' '}
                <span className="text-gray-200">{Math.round(bounds.minX)}</span>
              </div>
              <div>
                <span className="text-gray-500">Y:</span>{' '}
                <span className="text-gray-200">{Math.round(bounds.minY)}</span>
              </div>
              <div>
                <span className="text-gray-500">W:</span>{' '}
                <span className="text-gray-200">{Math.round(bounds.width)}</span>
              </div>
              <div>
                <span className="text-gray-500">H:</span>{' '}
                <span className="text-gray-200">{Math.round(bounds.height)}</span>
              </div>
            </div>
          </Box>

          {/* Rotated Rectangle Angle Slider */}
          {(isRotated || selectedRegion.geometry.type === 'rectangle') && (
            <div>
              <Flex justify="between" align="center" mb="1.5">
                <Text size="2" weight="bold" className="text-gray-200">
                  Rotation Angle
                </Text>
                <Text size="1" color="gray" className="font-mono">
                  {currentAngle.toFixed(1)}°
                </Text>
              </Flex>
              <Slider
                min={-180}
                max={180}
                step={0.5}
                value={[currentAngle]}
                onValueChange={([val]) => updateRegionAngle(selectedRegion.id, val)}
              />
            </div>
          )}

          {/* Padding Controls */}
          <div>
            <Flex justify="between" align="center" mb="1.5">
              <Text size="2" weight="bold" className="text-gray-200">
                Padding (px)
              </Text>
              <Flex gap="1">
                {[0, 20, 40, 80].map((px) => (
                  <Button
                    key={px}
                    size="1"
                    variant="soft"
                    color="gray"
                    onClick={() => applyPresetPadding(px)}
                    className="text-[10px] px-1.5 h-5"
                  >
                    {px}
                  </Button>
                ))}
              </Flex>
            </Flex>

            <div className="grid grid-cols-2 gap-2">
              <label>
                <Text size="1" color="gray" as="div" mb="0.5">
                  Top
                </Text>
                <TextField.Root
                  size="1"
                  type="number"
                  value={selectedRegion.padding.top}
                  onChange={(e) => handlePaddingChange('top', e.target.value)}
                />
              </label>
              <label>
                <Text size="1" color="gray" as="div" mb="0.5">
                  Right
                </Text>
                <TextField.Root
                  size="1"
                  type="number"
                  value={selectedRegion.padding.right}
                  onChange={(e) => handlePaddingChange('right', e.target.value)}
                />
              </label>
              <label>
                <Text size="1" color="gray" as="div" mb="0.5">
                  Bottom
                </Text>
                <TextField.Root
                  size="1"
                  type="number"
                  value={selectedRegion.padding.bottom}
                  onChange={(e) => handlePaddingChange('bottom', e.target.value)}
                />
              </label>
              <label>
                <Text size="1" color="gray" as="div" mb="0.5">
                  Left
                </Text>
                <TextField.Root
                  size="1"
                  type="number"
                  value={selectedRegion.padding.left}
                  onChange={(e) => handlePaddingChange('left', e.target.value)}
                />
              </label>
            </div>
          </div>

          <Separator size="4" />

          {/* Export Formats */}
          <div>
            <Text size="2" weight="bold" className="text-gray-200" mb="2" as="div">
              Export Outputs
            </Text>
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between p-2.5 rounded bg-gray-800/80 border border-gray-700/60">
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-gray-200">Archive Image</span>
                  <span className="text-[11px] text-gray-400">TIFF / Lossless PNG</span>
                </div>
                <Switch
                  size="2"
                  checked={selectedRegion.export.archive}
                  onCheckedChange={(c) => updateRegionExport(selectedRegion.id, { archive: c })}
                />
              </div>

              <div className="flex items-center justify-between p-2.5 rounded bg-gray-800/80 border border-gray-700/60">
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-gray-200">Clean Cutout</span>
                  <span className="text-[11px] text-gray-400">Isolated Transparent PNG</span>
                </div>
                <Switch
                  size="2"
                  checked={selectedRegion.export.clean}
                  onCheckedChange={(c) => updateRegionExport(selectedRegion.id, { clean: c })}
                />
              </div>

              <div className="flex items-center justify-between p-2.5 rounded bg-gray-800/80 border border-gray-700/60">
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-gray-200">Vector Curves</span>
                  <span className="text-[11px] text-gray-400">Scalable SVG (VTracer)</span>
                </div>
                <Switch
                  size="2"
                  checked={selectedRegion.export.vector}
                  onCheckedChange={(c) => updateRegionExport(selectedRegion.id, { vector: c })}
                />
              </div>

              <Button
                size="2"
                variant="soft"
                color="violet"
                className="w-full mt-1 cursor-pointer"
                onClick={() => setVectorModalOpen(true)}
              >
                <MagicWandIcon /> Vector Preview & Tuning...
              </Button>
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Action Footer */}
      <Box p="3" className="border-t border-gray-800 bg-gray-950/60 space-y-2">
        <Flex gap="2">
          <Button
            color="green"
            variant={selectedRegion.status === 'APPROVED' ? 'solid' : 'soft'}
            className="flex-1"
            onClick={() => updateRegionStatus(selectedRegion.id, 'APPROVED')}
          >
            <CheckIcon /> Approve
          </Button>

          <Button
            color="red"
            variant={selectedRegion.status === 'REJECTED' ? 'solid' : 'soft'}
            className="flex-1"
            onClick={() => updateRegionStatus(selectedRegion.id, 'REJECTED')}
          >
            <Cross2Icon /> Reject
          </Button>
        </Flex>

        <Button
          color="gray"
          variant="outline"
          className="w-full text-red-400 hover:text-red-300"
          onClick={() => deleteRegion(selectedRegion.id)}
        >
          <TrashIcon /> Delete Region
        </Button>

        <Flex justify="between" align="center" pt="1">
          <Text size="1" color="gray" className="text-[10px]">
            Autosave:{' '}
            {saveStatus === 'saving'
              ? 'Saving...'
              : saveStatus === 'error'
                ? 'Save Error'
                : 'Saved'}
          </Text>
        </Flex>
      </Box>

      <VectorPreviewDialog
        open={vectorModalOpen}
        pageId={currentPage?.id || null}
        regionId={selectedRegion.id}
        onClose={() => setVectorModalOpen(false)}
      />
    </Box>
  );
}
