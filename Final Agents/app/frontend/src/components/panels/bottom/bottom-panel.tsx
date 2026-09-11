import { useLayoutContext } from '@/contexts/layout-context';
import { useResizable } from '@/hooks/use-resizable';
import { cn } from '@/lib/utils';
import { FileText, Scale, X } from 'lucide-react';
import { ReactNode, useEffect } from 'react';
import { Button } from '../../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { useFlowContext } from '@/contexts/flow-context';
import { useNodeContext } from '@/contexts/node-context';
import { OutputTab } from './tabs';
import { DebateView } from './tabs/debate-view';

interface BottomPanelProps {
  children?: ReactNode;
  isCollapsed: boolean;
  onCollapse: () => void;
  onExpand: () => void;
  onToggleCollapse: () => void;
  onHeightChange?: (height: number) => void;
}

export function BottomPanel({
  isCollapsed,
  onToggleCollapse,
  onHeightChange,
}: BottomPanelProps) {
  const { currentBottomTab, setBottomPanelTab } = useLayoutContext();
  const { currentFlowId } = useFlowContext();
  const { getOutputNodeDataForFlow } = useNodeContext();
  const outputData = getOutputNodeDataForFlow(currentFlowId?.toString() || null);
  
  // Use our custom hooks for vertical resizing
  const { height, isDragging, elementRef, startResize } = useResizable({
    defaultHeight: 300,
    minHeight: 200,
    maxHeight: window.innerHeight,
    side: 'bottom',
  });
  
  // Notify parent component of height changes
  useEffect(() => {
    onHeightChange?.(height);
  }, [height, onHeightChange]);

  if (isCollapsed) {
    return null;
  }

  return (
    <div 
      ref={elementRef}
      className={cn(
        "bg-panel flex flex-col relative border-t",
        isDragging ? "select-none" : ""
      )}
      style={{ 
        height: `${height}px`,
      }}
    >
      {/* Resize handle - on the top for bottom panel */}
      {!isDragging && (
        <div 
          className="absolute top-0 left-0 right-0 h-1 cursor-ns-resize transition-all duration-150 z-10 hover-bg"
          onMouseDown={startResize}
        />
      )}

      <Tabs
        value={currentBottomTab}
        onValueChange={setBottomPanelTab}
        className="flex flex-col flex-1 min-h-0"
      >
        {/* Header with tabs and close button */}
        <div className="flex items-center justify-between border-b px-4 py-2">
          <div className="flex items-center justify-between flex-1">
            <TabsList className="bg-transparent border-none p-0 h-auto">
              <TabsTrigger
                value="output"
                className="flex items-center gap-2 px-3 py-1.5 text-sm data-[state=active]:active-item text-muted-foreground"
              >
                <FileText size={14} />
                Output
              </TabsTrigger>
              <TabsTrigger
                value="debate"
                className="flex items-center gap-2 px-3 py-1.5 text-sm data-[state=active]:active-item text-muted-foreground"
              >
                <Scale size={14} />
                Debate
              </TabsTrigger>
            </TabsList>

            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="h-6 w-6 text-primary hover-bg"
              aria-label="Close panel"
            >
              <X size={14} />
            </Button>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <TabsContent value="output" className="h-full m-0 p-4 data-[state=inactive]:hidden">
            <OutputTab className="h-full" />
          </TabsContent>
          <TabsContent value="debate" className="h-full m-0 p-4 overflow-hidden data-[state=inactive]:hidden">
            <DebateView outputData={outputData} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
} 