import { useState, useEffect, useCallback } from 'react';
import {
  Badge,
  Box,
  Button,
  Dialog,
  Flex,
  Heading,
  Select,
  Separator,
  Slider,
  Tabs,
  Text,
} from '@radix-ui/themes';
import {
  CodeIcon,
  DownloadIcon,
  EyeOpenIcon,
  MagicWandIcon,
  ReloadIcon,
} from '@radix-ui/react-icons';
import { VectorPreviewResult, VTracerPreset } from '../types/vector';
import * as api from '../api/client';

interface VectorPreviewDialogProps {
  open: boolean;
  pageId: string | null;
  regionId: string | null;
  onClose: () => void;
}

export function VectorPreviewDialog({ open, pageId, regionId, onClose }: VectorPreviewDialogProps) {
  const [presets, setPresets] = useState<VTracerPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('historical_bw');
  const [speckle, setSpeckle] = useState<number>(4);
  const [cornerThreshold, setCornerThreshold] = useState<number>(60);
  const [precision, setPrecision] = useState<number>(3);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<VectorPreviewResult | null>(null);
  const [activeTab, setActiveTab] = useState<'preview' | 'code'>('preview');

  // Load presets
  useEffect(() => {
    if (open) {
      api
        .fetchVectorPresets()
        .then((res) => {
          setPresets(res);
        })
        .catch(console.error);
    }
  }, [open]);

  // Load preview
  const generatePreview = useCallback(
    async (
      presetId = selectedPreset,
      customParams = {
        filter_speckle: speckle,
        corner_threshold: cornerThreshold,
        path_precision: precision,
      }
    ) => {
      if (!pageId || !regionId) return;
      setIsLoading(true);
      try {
        const res = await api.previewVectorRegion(pageId, regionId, {
          preset_id: presetId,
          custom_params: customParams,
        });
        setResult(res);
      } catch (err) {
        console.error('Vector preview error', err);
      } finally {
        setIsLoading(false);
      }
    },
    [pageId, regionId, selectedPreset, speckle, cornerThreshold, precision]
  );

  useEffect(() => {
    if (open && pageId && regionId) {
      generatePreview();
    }
  }, [open, pageId, regionId, generatePreview]);

  const handlePresetChange = (val: string) => {
    setSelectedPreset(val);
    const p = presets.find((x) => x.id === val);
    if (p) {
      setSpeckle(p.params.filter_speckle);
      setCornerThreshold(p.params.corner_threshold);
      setPrecision(p.params.path_precision);
      generatePreview(val, {
        filter_speckle: p.params.filter_speckle,
        corner_threshold: p.params.corner_threshold,
        path_precision: p.params.path_precision,
      });
    }
  };

  const handleDownloadSVG = () => {
    if (!result) return;
    const blob = new Blob([result.svg_content], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vector_illustration_${regionId}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!open) return null;

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Content className="max-w-4xl bg-gray-900 border border-gray-800 text-gray-100 p-0 overflow-hidden">
        <Flex direction="column" className="h-[640px]">
          {/* Header */}
          <Flex
            justify="between"
            align="center"
            px="4"
            py="3"
            className="border-b border-gray-800 bg-gray-950"
          >
            <Flex align="center" gap="2">
              <MagicWandIcon className="text-violet-400 w-5 h-5" />
              <Heading size="3">VTracer Vector Preview & Tuning</Heading>
            </Flex>
            <Flex align="center" gap="2">
              {result && (
                <>
                  <Badge color="violet" size="1">
                    {result.path_count} SVG paths
                  </Badge>
                  <Badge color="blue" size="1">
                    {(result.file_size_bytes / 1024).toFixed(1)} KB
                  </Badge>
                  <Badge color="green" size="1">
                    {result.elapsed_ms} ms
                  </Badge>
                </>
              )}
            </Flex>
          </Flex>

          {/* Body: Split View */}
          <Flex className="flex-1 overflow-hidden">
            {/* Left Column: Parameter Controls */}
            <Box className="w-80 border-r border-gray-800 p-4 space-y-4 overflow-y-auto bg-gray-900/60">
              <div>
                <Text size="2" weight="bold" mb="1" as="div">
                  Vectorization Preset
                </Text>
                <Select.Root value={selectedPreset} onValueChange={handlePresetChange}>
                  <Select.Trigger className="w-full" />
                  <Select.Content>
                    {presets.map((p) => (
                      <Select.Item key={p.id} value={p.id}>
                        {p.name}
                      </Select.Item>
                    ))}
                  </Select.Content>
                </Select.Root>
                <Text size="1" color="gray" mt="1" as="div">
                  {presets.find((p) => p.id === selectedPreset)?.description}
                </Text>
              </div>

              <Separator size="4" />

              {/* Parameter Sliders */}
              <div className="space-y-3">
                <div>
                  <Flex justify="between" align="center" mb="1">
                    <Text size="2">Speckle Filter (Noise)</Text>
                    <Text size="2" className="font-mono text-violet-400">
                      {speckle} px
                    </Text>
                  </Flex>
                  <Slider
                    value={[speckle]}
                    onValueChange={([v]) => setSpeckle(v)}
                    min={1}
                    max={16}
                    step={1}
                  />
                </div>

                <div>
                  <Flex justify="between" align="center" mb="1">
                    <Text size="2">Corner Threshold</Text>
                    <Text size="2" className="font-mono text-violet-400">
                      {cornerThreshold}°
                    </Text>
                  </Flex>
                  <Slider
                    value={[cornerThreshold]}
                    onValueChange={([v]) => setCornerThreshold(v)}
                    min={10}
                    max={120}
                    step={5}
                  />
                </div>

                <div>
                  <Flex justify="between" align="center" mb="1">
                    <Text size="2">Path Precision</Text>
                    <Text size="2" className="font-mono text-violet-400">
                      {precision}
                    </Text>
                  </Flex>
                  <Slider
                    value={[precision]}
                    onValueChange={([v]) => setPrecision(v)}
                    min={1}
                    max={8}
                    step={1}
                  />
                </div>
              </div>

              <Button
                variant="soft"
                color="violet"
                className="w-full"
                onClick={() => generatePreview()}
                disabled={isLoading}
              >
                <ReloadIcon className={isLoading ? 'animate-spin' : ''} />
                {isLoading ? 'Tracing Vector...' : 'Update Preview'}
              </Button>

              <Separator size="4" />

              <Button
                variant="solid"
                color="green"
                className="w-full"
                onClick={handleDownloadSVG}
                disabled={!result}
              >
                <DownloadIcon /> Download SVG
              </Button>
            </Box>

            {/* Right Column: Live SVG Rendering Canvas */}
            <Flex direction="column" className="flex-1 bg-gray-950">
              <Flex
                justify="between"
                align="center"
                px="3"
                py="1.5"
                className="border-b border-gray-800 bg-gray-900/40"
              >
                <Tabs.Root value={activeTab} onValueChange={(v: any) => setActiveTab(v)}>
                  <Tabs.List size="1">
                    <Tabs.Trigger value="preview">
                      <EyeOpenIcon /> SVG Preview
                    </Tabs.Trigger>
                    <Tabs.Trigger value="code">
                      <CodeIcon /> SVG Source
                    </Tabs.Trigger>
                  </Tabs.List>
                </Tabs.Root>
              </Flex>

              <Box className="flex-1 p-4 overflow-auto flex items-center justify-center relative">
                {activeTab === 'preview' ? (
                  result ? (
                    <div
                      className="max-w-full max-h-full flex items-center justify-center p-4 rounded bg-white shadow-2xl overflow-hidden"
                      dangerouslySetInnerHTML={{ __html: result.svg_content }}
                    />
                  ) : (
                    <Text color="gray" size="2">
                      {isLoading ? 'Generating vector...' : 'No preview available'}
                    </Text>
                  )
                ) : (
                  <pre className="text-xs font-mono text-gray-300 w-full h-full p-3 bg-gray-900 rounded overflow-auto select-text">
                    {result?.svg_content || 'No SVG generated'}
                  </pre>
                )}
              </Box>
            </Flex>
          </Flex>

          {/* Footer */}
          <Flex justify="end" px="4" py="2.5" className="border-t border-gray-800 bg-gray-950">
            <Button variant="soft" color="gray" onClick={onClose}>
              Close
            </Button>
          </Flex>
        </Flex>
      </Dialog.Content>
    </Dialog.Root>
  );
}
