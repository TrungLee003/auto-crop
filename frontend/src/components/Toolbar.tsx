import { useState } from 'react';
import {
  Badge,
  Button,
  DropdownMenu,
  Flex,
  IconButton,
  Separator,
  Text,
  Tooltip,
} from '@radix-ui/themes';
import {
  BlendingModeIcon,
  CheckCircledIcon,
  CropIcon,
  DownloadIcon,
  FileTextIcon,
  HandIcon,
  LoopIcon,
  MagicWandIcon,
  Pencil1Icon,
  PlusIcon,
  ResetIcon,
  Share1Icon,
  SquareIcon,
  TransparencyGridIcon,
  TrashIcon,
} from '@radix-ui/react-icons';
import { useProjectStore } from '../stores/projectStore';
import { usePageStore } from '../stores/pageStore';
import { useAnnotationStore } from '../stores/annotationStore';
import { ProjectDialog } from './ProjectDialog';
import { ImportDialog } from './ImportDialog';
import { BatchDetectDialog } from './BatchDetectDialog';
import { ExportDialog } from './ExportDialog';

export function Toolbar() {
  const { currentProject, closeProject, deleteProject } = useProjectStore();
  const { currentPage, pages, deletePage } = usePageStore();
  const {
    activeTool,
    setActiveTool,
    selectedRegionId,
    selectedRegionIds,
    regions,
    deleteRegion,
    fitSelectedRegion,
    mergeSelectedRegions,
    detectCurrentPage,
    approveAllPageRegions,
    isDetecting,
    isFitting,
    undo,
    redo,
    undoStack,
    redoStack,
    saveStatus,
  } = useAnnotationStore();

  const [projectDialogMode, setProjectDialogMode] = useState<'new' | 'open' | null>(null);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [batchDetectOpen, setBatchDetectOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);

  const hasUnapproved = regions.some((r) => r.status !== 'APPROVED');

  return (
    <>
      <Flex
        align="center"
        justify="between"
        px="3"
        py="2"
        className="border-b border-gray-800 bg-gray-900 select-none"
      >
        {/* Left: Project Controls & Name */}
        <Flex align="center" gap="3">
          <DropdownMenu.Root>
            <DropdownMenu.Trigger>
              <Button variant="surface" size="1">
                Project ▾
              </Button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Content size="1">
              <DropdownMenu.Item onClick={() => setProjectDialogMode('new')}>
                <PlusIcon /> New Project...
              </DropdownMenu.Item>
              <DropdownMenu.Item onClick={() => setProjectDialogMode('open')}>
                <FileTextIcon /> Open Project...
              </DropdownMenu.Item>
              <DropdownMenu.Separator />
              <DropdownMenu.Item
                disabled={!currentProject}
                onClick={() => setImportDialogOpen(true)}
              >
                <DownloadIcon /> Import Scans...
              </DropdownMenu.Item>
              <DropdownMenu.Item
                disabled={!currentProject}
                onClick={() => setBatchDetectOpen(true)}
              >
                <MagicWandIcon /> Batch Auto-Detect...
              </DropdownMenu.Item>
              <DropdownMenu.Separator />
              <DropdownMenu.Item
                disabled={!currentProject}
                onClick={() => setExportDialogOpen(true)}
              >
                <Share1Icon /> Export Illustrations...
              </DropdownMenu.Item>
              <DropdownMenu.Separator />
              <DropdownMenu.Item
                color="red"
                disabled={!currentPage}
                onClick={() => {
                  if (
                    currentPage &&
                    window.confirm(
                      `Delete page "${currentPage.filename}" (#${currentPage.sequence}) from project?`
                    )
                  ) {
                    deletePage(currentPage.id);
                  }
                }}
              >
                <TrashIcon /> Delete Current Page
              </DropdownMenu.Item>
              <DropdownMenu.Separator />
              <DropdownMenu.Item
                disabled={!currentProject}
                onClick={() => closeProject()}
              >
                Close Project
              </DropdownMenu.Item>
              <DropdownMenu.Item
                color="red"
                disabled={!currentProject}
                onClick={async () => {
                  if (!currentProject) return;
                  if (
                    window.confirm(
                      `Are you sure you want to delete project "${currentProject.name}"?`
                    )
                  ) {
                    const deleteDisk = window.confirm(
                      'Do you also want to permanently delete all project files from disk?'
                    );
                    await deleteProject(currentProject.project_id, deleteDisk);
                  }
                }}
              >
                <TrashIcon /> Delete Project...
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Root>

          {currentProject ? (
            <Flex align="center" gap="2">
              <Text weight="bold" size="2" className="text-white">
                {currentProject.name}
              </Text>
              <Badge color="blue" size="1">
                {pages.length} page(s)
              </Badge>
            </Flex>
          ) : (
            <Text size="2" color="gray">
              No project open
            </Text>
          )}

          {currentPage && (
            <>
              <Separator orientation="vertical" />
              <Text size="2" className="text-gray-300 font-mono">
                {currentPage.filename}
              </Text>
              <Badge color="gray" size="1">
                {currentPage.width} × {currentPage.height} px
              </Badge>
            </>
          )}
        </Flex>

        {/* Center: Annotation Drawing Tools, Auto-detect, Fit, Merge & Undo/Redo */}
        <Flex align="center" gap="2">
          <Tooltip content="Select / Pan (V)">
            <IconButton
              variant={activeTool === 'select' ? 'solid' : 'ghost'}
              size="1"
              onClick={() => setActiveTool('select')}
            >
              <HandIcon />
            </IconButton>
          </Tooltip>

          <Tooltip content="Draw Rectangle (R)">
            <IconButton
              variant={activeTool === 'rectangle' ? 'solid' : 'ghost'}
              size="1"
              onClick={() => setActiveTool('rectangle')}
              disabled={!currentPage}
            >
              <SquareIcon />
            </IconButton>
          </Tooltip>

          <Tooltip content="Draw Rotated Rectangle (O)">
            <IconButton
              variant={activeTool === 'rotated_rect' ? 'solid' : 'ghost'}
              size="1"
              onClick={() => setActiveTool('rotated_rect')}
              disabled={!currentPage}
            >
              <LoopIcon />
            </IconButton>
          </Tooltip>

          <Tooltip content="Draw Polygon (P) — Click points, double-click to finish">
            <IconButton
              variant={activeTool === 'polygon' ? 'solid' : 'ghost'}
              size="1"
              onClick={() => setActiveTool('polygon')}
              disabled={!currentPage}
            >
              <TransparencyGridIcon />
            </IconButton>
          </Tooltip>

          <Tooltip content="Draw Lasso / Freehand (L) — Freehand drag">
            <IconButton
              variant={activeTool === 'lasso' ? 'solid' : 'ghost'}
              size="1"
              onClick={() => setActiveTool('lasso')}
              disabled={!currentPage}
            >
              <Pencil1Icon />
            </IconButton>
          </Tooltip>

          <Separator orientation="vertical" />

          {/* Auto-detect Page */}
          <Tooltip content="Auto-Detect Illustrations on Page (Magic Wand)">
            <Button
              size="1"
              variant="soft"
              color="indigo"
              disabled={!currentPage || isDetecting}
              onClick={() => detectCurrentPage()}
            >
              <MagicWandIcon /> {isDetecting ? 'Detecting...' : 'Auto-Detect'}
            </Button>
          </Tooltip>

          {/* Fit to Content */}
          <Tooltip content="Fit to Ink Content (F) — Snaps bounds tightly around illustration">
            <Button
              size="1"
              variant="soft"
              color="indigo"
              disabled={!selectedRegionId || isFitting}
              onClick={fitSelectedRegion}
            >
              <CropIcon /> {isFitting ? 'Fitting...' : 'Fit Ink'}
            </Button>
          </Tooltip>

          {/* Merge Regions */}
          {selectedRegionIds.length >= 2 && (
            <Tooltip content="Merge Selected Regions">
              <Button size="1" variant="soft" color="violet" onClick={mergeSelectedRegions}>
                <BlendingModeIcon /> Merge ({selectedRegionIds.length})
              </Button>
            </Tooltip>
          )}

          {/* Approve All */}
          {regions.length > 0 && hasUnapproved && (
            <Tooltip content="Approve All Regions on Page (Shift+Enter)">
              <Button size="1" variant="soft" color="green" onClick={approveAllPageRegions}>
                <CheckCircledIcon /> Approve All
              </Button>
            </Tooltip>
          )}

          <Separator orientation="vertical" />

          <Tooltip content="Undo (Ctrl+Z)">
            <IconButton variant="ghost" size="1" disabled={undoStack.length === 0} onClick={undo}>
              <ResetIcon className="transform -scale-x-100" />
            </IconButton>
          </Tooltip>

          <Tooltip content="Redo (Ctrl+Shift+Z)">
            <IconButton variant="ghost" size="1" disabled={redoStack.length === 0} onClick={redo}>
              <ResetIcon />
            </IconButton>
          </Tooltip>

          <Separator orientation="vertical" />

          <Tooltip content="Delete Selected (Delete)">
            <IconButton
              variant="ghost"
              color="red"
              size="1"
              disabled={!selectedRegionId}
              onClick={() => selectedRegionId && deleteRegion(selectedRegionId)}
            >
              <TrashIcon />
            </IconButton>
          </Tooltip>
        </Flex>

        {/* Right: Autosave status badge, Export & Import buttons */}
        <Flex align="center" gap="2">
          {currentPage && (
            <Badge
              size="1"
              color={saveStatus === 'saving' ? 'amber' : saveStatus === 'error' ? 'red' : 'green'}
              variant="soft"
            >
              {saveStatus === 'saving'
                ? 'Saving...'
                : saveStatus === 'error'
                  ? 'Save Error'
                  : 'Autosaved'}
            </Badge>
          )}

          {currentProject && (
            <>
              <Button
                size="1"
                variant="solid"
                color="blue"
                onClick={() => setExportDialogOpen(true)}
              >
                <Share1Icon /> Export
              </Button>

              <Button
                size="1"
                variant="soft"
                color="indigo"
                onClick={() => setBatchDetectOpen(true)}
              >
                <MagicWandIcon /> Batch Detect
              </Button>

              <Button size="1" variant="soft" onClick={() => setImportDialogOpen(true)}>
                <DownloadIcon /> Import Scans
              </Button>
            </>
          )}
        </Flex>
      </Flex>

      <ProjectDialog mode={projectDialogMode} onClose={() => setProjectDialogMode(null)} />
      <ImportDialog open={importDialogOpen} onClose={() => setImportDialogOpen(false)} />
      <BatchDetectDialog open={batchDetectOpen} onClose={() => setBatchDetectOpen(false)} />
      <ExportDialog open={exportDialogOpen} onClose={() => setExportDialogOpen(false)} />
    </>
  );
}
