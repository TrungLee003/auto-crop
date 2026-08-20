import { useState, useEffect, useRef } from 'react';
import {
  Button,
  Dialog,
  Flex,
  Heading,
  Progress,
  RadioGroup,
  Select,
  Separator,
  Slider,
  Switch,
  Text,
} from '@radix-ui/themes';
import { MagicWandIcon, PlayIcon, Cross2Icon } from '@radix-ui/react-icons';
import { useProjectStore } from '../stores/projectStore';
import { usePageStore } from '../stores/pageStore';
import { useAnnotationStore } from '../stores/annotationStore';
import { DetectionConfig, TaskStatus } from '../types/detection';
import * as api from '../api/client';

interface BatchDetectDialogProps {
  open: boolean;
  onClose: () => void;
}

export function BatchDetectDialog({ open, onClose }: BatchDetectDialogProps) {
  const currentProject = useProjectStore((s) => s.currentProject);
  const { loadPages, currentPage } = usePageStore();
  const { loadRegions } = useAnnotationStore();

  const [filterStatus, setFilterStatus] = useState<'NEW' | 'ALL'>('NEW');
  const [preset, setPreset] = useState<'historical_line_art' | 'dense_woodcut' | 'custom'>(
    'historical_line_art'
  );
  const [sensitivity, setSensitivity] = useState<number>(0.5);
  const [textSuppression, setTextSuppression] = useState<boolean>(true);

  // Background Task state
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [isStarting, setIsStarting] = useState<boolean>(false);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Polling loop for background task progress
  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const status = await api.fetchTaskStatus(taskId);
        setTaskStatus(status);

        if (
          status.status === 'completed' ||
          status.status === 'failed' ||
          status.status === 'cancelled'
        ) {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;

          // Reload pages to reflect new region counts and statuses
          if (currentProject) {
            loadPages(currentProject.project_id);
          }
          if (currentPage) {
            loadRegions(currentPage.id);
          }
        }
      } catch (err) {
        console.error('Error polling task status', err);
      }
    };

    poll();
    pollIntervalRef.current = setInterval(poll, 600);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [taskId, currentProject, currentPage, loadPages, loadRegions]);

  const handleStart = async () => {
    if (!currentProject) return;

    setIsStarting(true);
    try {
      const config: DetectionConfig = {
        preset,
        sensitivity,
        text_suppression: textSuppression,
        min_area_ratio: 0.001,
        max_area_ratio: 0.92,
      };

      const res = await api.startBatchDetect(currentProject.project_id, filterStatus, config);
      setTaskId(res.task_id);
      setIsStarting(false);
    } catch (err: any) {
      alert(err.message || 'Failed to start batch detection');
      setIsStarting(false);
    }
  };

  const handleCancel = async () => {
    if (!taskId) return;
    try {
      await api.cancelTask(taskId);
    } catch (err) {
      console.error('Cancel task failed', err);
    }
  };

  const handleClose = () => {
    if (taskStatus?.status === 'running') {
      // Allow dialog to close while task runs in background
      onClose();
    } else {
      setTaskId(null);
      setTaskStatus(null);
      onClose();
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && handleClose()}>
      <Dialog.Content className="max-w-md bg-gray-900 border border-gray-800 text-gray-100">
        <Dialog.Title>
          <Flex align="center" gap="2">
            <MagicWandIcon className="text-indigo-400 w-5 h-5" />
            <Heading size="4">Batch Auto-Detection</Heading>
          </Flex>
        </Dialog.Title>

        <Dialog.Description size="2" color="gray" mb="4">
          Automatically detect illustrations and ornaments across book scan pages using the OpenCV
          rule-based detection engine.
        </Dialog.Description>

        {!taskId ? (
          <div className="space-y-4">
            {/* Scope Selection */}
            <div>
              <Text size="2" weight="bold" mb="1" as="div">
                Target Pages
              </Text>
              <RadioGroup.Root
                value={filterStatus}
                onValueChange={(val) => setFilterStatus(val as 'NEW' | 'ALL')}
              >
                <Flex direction="column" gap="2">
                  <Text as="label" size="2">
                    <Flex gap="2" align="center">
                      <RadioGroup.Item value="NEW" />
                      <span>New / Unprocessed pages only</span>
                    </Flex>
                  </Text>
                  <Text as="label" size="2">
                    <Flex gap="2" align="center">
                      <RadioGroup.Item value="ALL" />
                      <span>All pages in project (re-detect)</span>
                    </Flex>
                  </Text>
                </Flex>
              </RadioGroup.Root>
            </div>

            <Separator size="4" />

            {/* Presets */}
            <div>
              <Text size="2" weight="bold" mb="1" as="div">
                Detection Preset
              </Text>
              <Select.Root value={preset} onValueChange={(val) => setPreset(val as any)}>
                <Select.Trigger className="w-full" />
                <Select.Content>
                  <Select.Item value="historical_line_art">
                    Historical Line Art (Woodcuts, Etchings)
                  </Select.Item>
                  <Select.Item value="dense_woodcut">Dense / Heavy Ink Illustrations</Select.Item>
                  <Select.Item value="custom">Custom Sensitivity</Select.Item>
                </Select.Content>
              </Select.Root>
            </div>

            {/* Sensitivity Slider */}
            <div>
              <Flex justify="between" align="center" mb="1">
                <Text size="2" weight="bold">
                  Sensitivity
                </Text>
                <Text size="1" color="gray" className="font-mono">
                  {Math.round(sensitivity * 100)}%
                </Text>
              </Flex>
              <Slider
                min={0.1}
                max={1.0}
                step={0.05}
                value={[sensitivity]}
                onValueChange={([val]) => setSensitivity(val)}
              />
              <Text size="1" color="gray" mt="1" as="div">
                Higher sensitivity detects fainter pencil/faded ink strokes.
              </Text>
            </div>

            {/* Text Suppression */}
            <Text as="label" size="2">
              <Flex align="center" gap="2">
                <Switch checked={textSuppression} onCheckedChange={setTextSuppression} />
                <span>Suppress running body text & page numbers</span>
              </Flex>
            </Text>

            <Flex gap="3" justify="end" mt="5">
              <Dialog.Close>
                <Button variant="soft" color="gray">
                  Cancel
                </Button>
              </Dialog.Close>
              <Button color="indigo" onClick={handleStart} disabled={isStarting || !currentProject}>
                <PlayIcon /> Start Batch Detection
              </Button>
            </Flex>
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {/* Progress Display */}
            <div>
              <Flex justify="between" align="center" mb="2">
                <Text size="2" weight="bold">
                  {taskStatus?.status === 'running'
                    ? 'Processing Scan Pages...'
                    : taskStatus?.status === 'completed'
                      ? 'Detection Finished!'
                      : taskStatus?.status === 'cancelled'
                        ? 'Detection Cancelled'
                        : 'Detection Failed'}
                </Text>
                <Text size="2" className="font-mono text-indigo-400">
                  {taskStatus?.progress || 0}%
                </Text>
              </Flex>

              <Progress value={taskStatus?.progress || 0} color="indigo" />

              <Text size="1" color="gray" mt="2" as="div">
                {taskStatus?.message || 'Preparing batch worker...'}
              </Text>
            </div>

            <Flex gap="3" justify="end" mt="5">
              {taskStatus?.status === 'running' ? (
                <>
                  <Button variant="soft" color="gray" onClick={handleClose}>
                    Run in Background
                  </Button>
                  <Button variant="soft" color="red" onClick={handleCancel}>
                    <Cross2Icon /> Cancel
                  </Button>
                </>
              ) : (
                <Button color="green" onClick={handleClose}>
                  Done
                </Button>
              )}
            </Flex>
          </div>
        )}
      </Dialog.Content>
    </Dialog.Root>
  );
}
