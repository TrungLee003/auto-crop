import { useState } from 'react';
import {
  Button,
  Dialog,
  Flex,
  Text,
  TextField,
  RadioGroup,
  Checkbox,
  Callout,
} from '@radix-ui/themes';
import { CheckCircledIcon, FileTextIcon, InfoCircledIcon } from '@radix-ui/react-icons';
import { useProjectStore } from '../stores/projectStore';
import { usePageStore } from '../stores/pageStore';
import * as api from '../api/client';
import { ImportMode, ImportResult } from '../types/project';

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ImportDialog({ open, onClose }: ImportDialogProps) {
  const currentProject = useProjectStore((s) => s.currentProject);
  const loadPages = usePageStore((s) => s.loadPages);

  const [folderPath, setFolderPath] = useState('');
  const [filePaths, setFilePaths] = useState<string[]>([]);
  const [mode, setMode] = useState<ImportMode>('COPY');
  const [recursive, setRecursive] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  if (!open || !currentProject) return null;

  const handleBrowseFolder = async () => {
    const electronAPI = (window as any).electronAPI;
    if (electronAPI?.openFolderPicker) {
      const selected = await electronAPI.openFolderPicker();
      if (selected) {
        setFolderPath(selected);
        setFilePaths([]);
      }
    }
  };

  const handleBrowseFiles = async () => {
    const electronAPI = (window as any).electronAPI;
    if (electronAPI?.openFilePicker) {
      const selected = await electronAPI.openFilePicker();
      if (selected && selected.length > 0) {
        setFilePaths(selected);
        setFolderPath('');
      }
    }
  };

  const handleImport = async () => {
    if (!folderPath.trim() && filePaths.length === 0) return;
    setIsImporting(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.importScans(
        currentProject.project_id,
        filePaths,
        folderPath.trim() || undefined,
        mode,
        recursive
      );
      setResult(res);
      await loadPages(currentProject.project_id);
    } catch (err: any) {
      setError(err.message || 'Import failed');
    } finally {
      setIsImporting(false);
    }
  };

  const handleClose = () => {
    setResult(null);
    setError(null);
    setFilePaths([]);
    onClose();
  };

  const hasElectron = Boolean((window as any).electronAPI?.openFolderPicker);

  return (
    <Dialog.Root open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <Dialog.Content maxWidth="540px">
        <Dialog.Title>Import Scans into Project</Dialog.Title>
        <Dialog.Description size="2" mb="4" color="gray">
          Select a folder or files containing book scans (TIFF, PNG, JPEG, WebP).
        </Dialog.Description>

        {error && (
          <Callout.Root color="red" mb="3">
            <Callout.Icon>
              <InfoCircledIcon />
            </Callout.Icon>
            <Callout.Text>{error}</Callout.Text>
          </Callout.Root>
        )}

        {result && (
          <Callout.Root color="green" mb="3">
            <Callout.Icon>
              <CheckCircledIcon />
            </Callout.Icon>
            <Callout.Text>
              Successfully imported {result.imported_count} scans. ({result.skipped_duplicates}{' '}
              duplicate(s) skipped).
            </Callout.Text>
          </Callout.Root>
        )}

        <Flex direction="column" gap="3">
          <div>
            <Text as="div" size="2" mb="1" weight="bold">
              Folder or File Source
            </Text>
            <Flex gap="2">
              <TextField.Root
                className="flex-1"
                placeholder="e.g. D:\Scans\Volume_1"
                value={filePaths.length > 0 ? `${filePaths.length} file(s) selected` : folderPath}
                onChange={(e) => {
                  setFolderPath(e.target.value);
                  setFilePaths([]);
                }}
              />
              {hasElectron && (
                <>
                  <Button type="button" variant="soft" color="gray" onClick={handleBrowseFolder}>
                    <FileTextIcon /> Folder...
                  </Button>
                  <Button type="button" variant="soft" color="gray" onClick={handleBrowseFiles}>
                    Files...
                  </Button>
                </>
              )}
            </Flex>
          </div>

          <Flex align="center" gap="2">
            <Checkbox checked={recursive} onCheckedChange={(c) => setRecursive(!!c)} />
            <Text size="2">Include subdirectories</Text>
          </Flex>

          <div>
            <Text size="2" weight="bold" mb="2">
              Import Mode
            </Text>
            <RadioGroup.Root value={mode} onValueChange={(val) => setMode(val as ImportMode)}>
              <Flex direction="column" gap="2">
                <Text as="label" size="2">
                  <Flex gap="2" align="center">
                    <RadioGroup.Item value="COPY" />
                    <div>
                      <Text weight="medium">COPY (Recommended)</Text>
                      <Text as="div" size="1" color="gray">
                        Copies scan files directly into project storage (fully self-contained).
                      </Text>
                    </div>
                  </Flex>
                </Text>
                <Text as="label" size="2">
                  <Flex gap="2" align="center">
                    <RadioGroup.Item value="REFERENCE" />
                    <div>
                      <Text weight="medium">REFERENCE</Text>
                      <Text as="div" size="1" color="gray">
                        Leaves scan files in original location, storing only path references.
                      </Text>
                    </div>
                  </Flex>
                </Text>
              </Flex>
            </RadioGroup.Root>
          </div>
        </Flex>

        <Flex gap="3" mt="5" justify="end">
          <Dialog.Close>
            <Button variant="soft" color="gray" onClick={handleClose}>
              Cancel
            </Button>
          </Dialog.Close>
          <Button
            onClick={handleImport}
            disabled={isImporting || (!folderPath.trim() && filePaths.length === 0)}
          >
            {isImporting ? 'Importing...' : 'Start Import'}
          </Button>
        </Flex>
      </Dialog.Content>
    </Dialog.Root>
  );
}
