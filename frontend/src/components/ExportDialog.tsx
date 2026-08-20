import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Button,
  Dialog,
  Flex,
  Heading,
  Progress,
  RadioGroup,
  Select,
  Separator,
  Switch,
  Text,
} from '@radix-ui/themes';
import { CheckCircledIcon, DownloadIcon, Cross2Icon, PlayIcon } from '@radix-ui/react-icons';
import { useProjectStore } from '../stores/projectStore';
import { ExportRequest, ExportScope } from '../types/export';
import * as api from '../api/client';

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ExportDialog({ open, onClose }: ExportDialogProps) {
  const currentProject = useProjectStore((s) => s.currentProject);

  const [scope, setScope] = useState<ExportScope>('APPROVED_ONLY');
  const [archiveFormat, setArchiveFormat] = useState<'PNG' | 'TIFF'>('PNG');
  const [archiveEnabled, setArchiveEnabled] = useState(true);
  const [cleanEnabled, setCleanEnabled] = useState(true);
  const [vectorEnabled, setVectorEnabled] = useState(true);

  // Background Task state
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<any | null>(null);
  const [exportDir, setExportDir] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Polling loop
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
        }
      } catch (err) {
        console.error('Error polling export task status', err);
      }
    };

    poll();
    pollIntervalRef.current = setInterval(poll, 600);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [taskId]);

  const handleStartExport = async () => {
    if (!currentProject) return;

    setIsStarting(true);
    try {
      const req: ExportRequest = {
        scope,
        formats: {
          archive: archiveEnabled,
          clean: cleanEnabled,
          vector: vectorEnabled,
        },
        archive_format: archiveFormat,
      };

      const res = await api.startExport(currentProject.project_id, req);
      setTaskId(res.task_id);
      setExportDir(res.export_dir);
      setIsStarting(false);
    } catch (err: any) {
      alert(err.message || 'Failed to start export');
      setIsStarting(false);
    }
  };

  const handleCancel = async () => {
    if (!taskId) return;
    try {
      await api.cancelTask(taskId);
    } catch (err) {
      console.error('Cancel export failed', err);
    }
  };

  const handleClose = () => {
    setTaskId(null);
    setTaskStatus(null);
    setExportDir(null);
    onClose();
  };

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && handleClose()}>
      <Dialog.Content className="max-w-md bg-gray-900 border border-gray-800 text-gray-100">
        <Dialog.Title>
          <Flex align="center" gap="2">
            <DownloadIcon className="text-blue-400 w-5 h-5" />
            <Heading size="4">Export Illustrations</Heading>
          </Flex>
        </Dialog.Title>

        <Dialog.Description size="2" color="gray" mb="4">
          Export cropped illustrations with 3 independent output streams, metadata sidecars, and
          catalog index.
        </Dialog.Description>

        {!taskId ? (
          <div className="space-y-4">
            {/* Scope Selection */}
            <div>
              <Text size="2" weight="bold" mb="1" as="div">
                Export Scope
              </Text>
              <RadioGroup.Root value={scope} onValueChange={(val) => setScope(val as ExportScope)}>
                <Flex direction="column" gap="2">
                  <Text as="label" size="2">
                    <Flex gap="2" align="center">
                      <RadioGroup.Item value="APPROVED_ONLY" />
                      <span>Approved illustrations only (Recommended)</span>
                    </Flex>
                  </Text>
                  <Text as="label" size="2">
                    <Flex gap="2" align="center">
                      <RadioGroup.Item value="ALL_EXCEPT_REJECTED" />
                      <span>All illustrations (Approved, Edited, Auto)</span>
                    </Flex>
                  </Text>
                </Flex>
              </RadioGroup.Root>
            </div>

            <Separator size="4" />

            {/* Output Formats */}
            <div>
              <Text size="2" weight="bold" mb="2" as="div">
                Output Streams
              </Text>
              <Flex direction="column" gap="3">
                <Flex justify="between" align="center">
                  <Text as="label" size="2">
                    <Flex align="center" gap="2">
                      <Switch checked={archiveEnabled} onCheckedChange={setArchiveEnabled} />
                      <span>Archive Master Resolution</span>
                    </Flex>
                  </Text>
                  <Select.Root
                    size="1"
                    value={archiveFormat}
                    onValueChange={(v) => setArchiveFormat(v as any)}
                    disabled={!archiveEnabled}
                  >
                    <Select.Trigger />
                    <Select.Content>
                      <Select.Item value="PNG">PNG (Lossless)</Select.Item>
                      <Select.Item value="TIFF">TIFF (Deflate, 300 DPI)</Select.Item>
                    </Select.Content>
                  </Select.Root>
                </Flex>

                <Text as="label" size="2">
                  <Flex align="center" gap="2">
                    <Switch checked={cleanEnabled} onCheckedChange={setCleanEnabled} />
                    <span>Clean Transparent PNG (Background removed)</span>
                  </Flex>
                </Text>

                <Text as="label" size="2">
                  <Flex align="center" gap="2">
                    <Switch checked={vectorEnabled} onCheckedChange={setVectorEnabled} />
                    <span>Vectorized SVG (VTracer splines)</span>
                  </Flex>
                </Text>
              </Flex>
            </div>

            <Separator size="4" />

            <div className="bg-gray-950/60 p-2.5 rounded border border-gray-800 text-xs text-gray-400 space-y-1 font-mono">
              <div>
                Output index: <span className="text-gray-200">catalog.csv</span>
              </div>
              <div>
                Metadata format: <span className="text-gray-200">metadata.json (JSON sidecar)</span>
              </div>
            </div>

            <Flex gap="3" justify="end" mt="5">
              <Dialog.Close>
                <Button variant="soft" color="gray">
                  Cancel
                </Button>
              </Dialog.Close>
              <Button
                color="blue"
                onClick={handleStartExport}
                disabled={isStarting || (!archiveEnabled && !cleanEnabled && !vectorEnabled)}
              >
                <PlayIcon /> Start Export
              </Button>
            </Flex>
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {/* Progress Bar */}
            <div>
              <Flex justify="between" align="center" mb="2">
                <Text size="2" weight="bold">
                  {taskStatus?.status === 'running'
                    ? 'Exporting Illustrations...'
                    : taskStatus?.status === 'completed'
                      ? 'Export Finished!'
                      : taskStatus?.status === 'cancelled'
                        ? 'Export Cancelled'
                        : 'Export Failed'}
                </Text>
                <Text size="2" className="font-mono text-blue-400">
                  {taskStatus?.progress || 0}%
                </Text>
              </Flex>

              <Progress value={taskStatus?.progress || 0} color="blue" />

              <Text size="1" color="gray" mt="2" as="div">
                {taskStatus?.message || 'Processing export streams...'}
              </Text>
            </div>

            {taskStatus?.status === 'completed' && exportDir && (
              <Box className="bg-gray-950/80 p-3 rounded border border-gray-800 text-xs space-y-2">
                <Flex align="center" gap="1.5" className="text-green-400 font-medium">
                  <CheckCircledIcon /> Export Successful
                </Flex>
                <div className="text-gray-400 font-mono text-[11px] break-all">
                  Location: <span className="text-gray-200">{exportDir}</span>
                </div>
              </Box>
            )}

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
