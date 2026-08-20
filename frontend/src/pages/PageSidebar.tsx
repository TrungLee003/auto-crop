import { Badge, Box, Button, Flex, Heading, ScrollArea, SegmentedControl, Text } from '@radix-ui/themes';
import { useProjectStore } from '../stores/projectStore';
import { PageFilter, usePageStore } from '../stores/pageStore';
import { PageModel, PageStatus } from '../types/project';

function getStatusBadge(status: PageStatus) {
  switch (status) {
    case 'NEW':
      return (
        <Badge color="gray" size="1">
          NEW
        </Badge>
      );
    case 'PROCESSING':
      return (
        <Badge color="amber" size="1">
          PROCESSING
        </Badge>
      );
    case 'DETECTED':
      return (
        <Badge color="blue" size="1">
          DETECTED
        </Badge>
      );
    case 'IN_REVIEW':
      return (
        <Badge color="yellow" size="1">
          IN REVIEW
        </Badge>
      );
    case 'REVIEWED':
      return (
        <Badge color="green" size="1">
          REVIEWED
        </Badge>
      );
    case 'EXPORTED':
      return (
        <Badge color="purple" size="1">
          EXPORTED
        </Badge>
      );
    case 'FAILED':
      return (
        <Badge color="red" size="1">
          FAILED
        </Badge>
      );
    default:
      return <Badge size="1">{status}</Badge>;
  }
}

export function PageSidebar() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const {
    pages,
    currentPage,
    filter,
    selectPage,
    setFilter,
    loadPages,
    deletePage,
    sortPages,
  } = usePageStore();

  const handleFilterChange = (val: string) => {
    const newFilter = val as PageFilter;
    setFilter(newFilter);
    if (currentProject) {
      loadPages(currentProject.project_id, newFilter);
    }
  };

  const naturalCompare = (a: string, b: string) =>
    a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });

  const sortedPages = [...pages]
    .filter((p) => (filter === 'ALL' ? true : p.status === filter))
    .sort((a, b) => {
      if (a.sequence !== b.sequence) return a.sequence - b.sequence;
      return naturalCompare(a.filename, b.filename);
    });

  return (
    <Box className="h-full flex flex-col bg-gray-900 border-r border-gray-800 select-none">
      {/* Header & Filter */}
      <Box p="3" className="border-b border-gray-800">
        <Flex justify="between" align="center" mb="2">
          <Heading size="3" className="text-gray-100">
            Pages
          </Heading>
          <Flex align="center" gap="2">
            <Text size="1" color="gray">
              {sortedPages.length} of {pages.length}
            </Text>
            {currentProject && (
              <Button
                size="1"
                variant="soft"
                color="gray"
                title="Sort all pages in natural alphanumeric order (1, 2, ... 10, ... 100)"
                onClick={() => sortPages(currentProject.project_id)}
                className="cursor-pointer text-[10px] px-1.5 h-5 font-mono"
              >
                Sort 1..N
              </Button>
            )}
          </Flex>
        </Flex>

        <SegmentedControl.Root
          value={filter}
          onValueChange={handleFilterChange}
          size="1"
          className="w-full"
        >
          <SegmentedControl.Item value="ALL">All</SegmentedControl.Item>
          <SegmentedControl.Item value="NEW">New</SegmentedControl.Item>
          <SegmentedControl.Item value="DETECTED">Detected</SegmentedControl.Item>
          <SegmentedControl.Item value="REVIEWED">Reviewed</SegmentedControl.Item>
        </SegmentedControl.Root>
      </Box>

      {/* Pages List */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-2">
          {!currentProject ? (
            <Box p="4" className="text-center text-gray-500">
              <Text size="2">Open or create a project to start importing scans.</Text>
            </Box>
          ) : sortedPages.length === 0 ? (
            <Box p="4" className="text-center text-gray-500">
              <Text size="2">No pages found in this filter.</Text>
            </Box>
          ) : (
            sortedPages.map((page: PageModel) => {
              const isSelected = currentPage?.id === page.id;
              return (
                <div
                  key={page.id}
                  onClick={() => selectPage(page.id)}
                  className={`p-2 rounded cursor-pointer transition-all border group relative ${
                    isSelected
                      ? 'bg-blue-950/60 border-blue-500 shadow-md shadow-blue-950/50'
                      : 'bg-gray-800/80 border-gray-700/60 hover:bg-gray-700/80 hover:border-gray-600'
                  }`}
                >
                  {/* Thumbnail Image */}
                  <div className="w-full h-28 bg-gray-950/80 rounded overflow-hidden flex items-center justify-center mb-1.5 border border-gray-800 relative">
                    <img
                      src={`/api/v2/pages/${page.id}/thumbnail`}
                      alt={page.filename}
                      className="max-h-full max-w-full object-contain"
                      loading="lazy"
                      onError={(e) => {
                        // fallback placeholder
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    <div className="absolute top-1 left-1 bg-black/70 px-1 rounded text-[10px] font-mono text-gray-300">
                      #{page.sequence}
                    </div>

                    {/* Delete page button */}
                    <button
                      type="button"
                      title="Delete page from project"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (
                          window.confirm(
                            `Delete page "${page.filename}" (#${page.sequence}) from this project?`
                          )
                        ) {
                          deletePage(page.id);
                        }
                      }}
                      className="absolute top-1 right-1 bg-black/70 hover:bg-red-600 text-gray-400 hover:text-white p-1 rounded opacity-0 group-hover:opacity-100 transition-all z-10"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="w-3.5 h-3.5"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </button>
                  </div>

                  {/* Metadata Row */}
                  <Flex justify="between" align="center">
                    <Text size="1" weight="bold" className="truncate text-gray-200 max-w-[140px]">
                      {page.filename}
                    </Text>
                    {getStatusBadge(page.status)}
                  </Flex>

                  {/* Resolution Row */}
                  <Flex justify="between" align="center" mt="1">
                    <Text size="1" color="gray" className="text-[11px] font-mono">
                      {page.width} × {page.height}
                    </Text>
                    {page.region_count > 0 && (
                      <Badge color="blue" size="1">
                        {page.region_count} regions
                      </Badge>
                    )}
                  </Flex>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>
    </Box>
  );
}
