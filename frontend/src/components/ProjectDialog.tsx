import { useState } from 'react';
import { Button, Dialog, Flex, Text, TextField, Callout } from '@radix-ui/themes';
import { FileTextIcon, InfoCircledIcon } from '@radix-ui/react-icons';
import { useProjectStore } from '../stores/projectStore';

interface ProjectDialogProps {
  mode: 'new' | 'open' | null;
  onClose: () => void;
}

export function ProjectDialog({ mode, onClose }: ProjectDialogProps) {
  const { createProject, openProject, recentPaths, isLoading, error, clearError } =
    useProjectStore();
  const [name, setName] = useState('');
  const [path, setPath] = useState('');

  if (!mode) return null;

  const handleBrowseFolder = async () => {
    const electronAPI = (window as any).electronAPI;
    if (electronAPI?.openFolderPicker) {
      const selected = await electronAPI.openFolderPicker();
      if (selected) setPath(selected);
    }
  };

  const handleSubmit = async () => {
    clearError();
    try {
      if (mode === 'new') {
        if (!name.trim()) return;
        await createProject(name.trim(), path.trim() || undefined);
      } else {
        if (!path.trim()) return;
        await openProject(path.trim());
      }
      onClose();
    } catch {
      // error handled in store
    }
  };

  const hasElectron = Boolean((window as any).electronAPI?.openFolderPicker);

  return (
    <Dialog.Root open={mode !== null} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Content maxWidth="500px">
        <Dialog.Title>
          {mode === 'new' ? 'Create New Project' : 'Open Existing Project'}
        </Dialog.Title>
        <Dialog.Description size="2" mb="4" color="gray">
          {mode === 'new'
            ? 'Set up a new illustration extraction workspace for your scanned book.'
            : 'Select a project folder containing project.json.'}
        </Dialog.Description>

        {error && (
          <Callout.Root color="red" mb="3">
            <Callout.Icon>
              <InfoCircledIcon />
            </Callout.Icon>
            <Callout.Text>{error}</Callout.Text>
          </Callout.Root>
        )}

        <Flex direction="column" gap="3">
          {mode === 'new' && (
            <label>
              <Text as="div" size="2" mb="1" weight="bold">
                Project Name
              </Text>
              <TextField.Root
                placeholder="e.g. Historical Atlas 1890"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}

          <div>
            <Text as="div" size="2" mb="1" weight="bold">
              {mode === 'new' ? 'Project Directory (optional)' : 'Project Directory'}
            </Text>
            <Flex gap="2">
              <TextField.Root
                className="flex-1"
                placeholder="e.g. D:\Books\Historical_Atlas"
                value={path}
                onChange={(e) => setPath(e.target.value)}
              />
              {hasElectron && (
                <Button type="button" variant="soft" color="gray" onClick={handleBrowseFolder}>
                  <FileTextIcon /> Browse...
                </Button>
              )}
            </Flex>
          </div>

          {mode === 'open' && recentPaths.length > 0 && (
            <div>
              <Text size="1" color="gray" mb="1">
                Recent Projects:
              </Text>
              <div className="max-h-28 overflow-y-auto space-y-1">
                {recentPaths.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setPath(p)}
                    className="w-full text-left text-xs p-1.5 rounded bg-gray-800 hover:bg-gray-700 truncate block text-gray-300"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}
        </Flex>

        <Flex gap="3" mt="4" justify="end">
          <Dialog.Close>
            <Button variant="soft" color="gray" onClick={onClose}>
              Cancel
            </Button>
          </Dialog.Close>
          <Button
            onClick={handleSubmit}
            disabled={isLoading || (mode === 'new' ? !name.trim() : !path.trim())}
          >
            {isLoading ? 'Processing...' : mode === 'new' ? 'Create Project' : 'Open'}
          </Button>
        </Flex>
      </Dialog.Content>
    </Dialog.Root>
  );
}
