import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

function scoreToPct(score: number): number {
  return Math.max(0, Math.min(100, ((Number(score) + 100) / 200) * 100));
}

function scoreColor(score: number): string {
  if (score > 20) return 'bg-emerald-500';
  if (score < -20) return 'bg-red-500';
  return 'bg-amber-500';
}

interface DebateViewProps {
  outputData: Record<string, unknown> | null;
}

/**
 * Shows agent score bars, bull/bear camps, and meta verdict when debate metadata exists.
 */
export function DebateView({ outputData }: DebateViewProps) {
  if (!outputData) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm">
        Run an analysis with debate enabled to see scores and meta verdict here.
      </div>
    );
  }

  const analystSignals = (outputData.analyst_signals || {}) as Record<string, Record<string, unknown>>;
  const debateResult = (outputData as { debate_result?: Record<string, unknown> }).debate_result;
  const metaOut = (outputData as { meta_agent_output?: Record<string, unknown> }).meta_agent_output;

  const decisions = (outputData as { decisions?: Record<string, unknown> }).decisions || {};
  let tickerList = Object.keys(decisions);
  if (tickerList.length === 0) {
    for (const per of Object.values(analystSignals)) {
      if (per && typeof per === 'object') {
        tickerList = Object.keys(per as Record<string, unknown>);
        break;
      }
    }
  }

  if (tickerList.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-6">
        No ticker context in output. Complete a hedge-fund run to populate debate view.
      </div>
    );
  }

  const t = tickerList[0];

  const agents: { id: string; score: number; steps?: string[]; conviction?: string }[] = [];
  for (const [agentId, perTicker] of Object.entries(analystSignals)) {
    if (agentId.includes('risk_management')) continue;
    const row = perTicker?.[t] as Record<string, unknown> | undefined;
    if (!row) continue;
    const sc = row.score !== undefined ? Number(row.score) : null;
    if (sc === null || Number.isNaN(sc)) continue;
    const steps = Array.isArray(row.reasoning_steps) ? (row.reasoning_steps as string[]) : undefined;
    agents.push({
      id: agentId,
      score: sc,
      steps,
      conviction: typeof row.conviction_reason === 'string' ? row.conviction_reason : undefined,
    });
  }

  const bulls = agents.filter((a) => a.score > 20);
  const bears = agents.filter((a) => a.score < -20);

  const meta = metaOut?.[t] as Record<string, unknown> | undefined;
  const debateT = debateResult?.[t] as Record<string, unknown> | undefined;

  return (
    <div className="space-y-4 text-sm overflow-y-auto h-full pr-1">
      <Card className="bg-transparent border-border/60">
        <CardHeader className="py-3">
          <CardTitle className="text-base">Agent scores ({t})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {agents.length === 0 && (
            <p className="text-muted-foreground">No scored agents in output (needs CoT scores).</p>
          )}
          {agents.map((a) => (
            <div key={a.id} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="font-medium truncate mr-2">{a.id}</span>
                <span>{a.score}</span>
              </div>
              <div className="h-2 w-full rounded bg-muted overflow-hidden">
                <div
                  className={cn('h-full transition-all', scoreColor(a.score))}
                  style={{ width: `${scoreToPct(a.score)}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="bg-transparent border-border/60">
        <CardHeader className="py-3">
          <CardTitle className="text-base">Bull vs bear camps</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <div className="font-semibold text-emerald-600 mb-1">Bull (score &gt; 20)</div>
            <ul className="list-disc pl-4 space-y-1">
              {bulls.map((b) => (
                <li key={b.id}>{b.id}</li>
              ))}
              {bulls.length === 0 && <li className="text-muted-foreground">None</li>}
            </ul>
          </div>
          <div>
            <div className="font-semibold text-red-600 mb-1">Bear (score &lt; -20)</div>
            <ul className="list-disc pl-4 space-y-1">
              {bears.map((b) => (
                <li key={b.id}>{b.id}</li>
              ))}
              {bears.length === 0 && <li className="text-muted-foreground">None</li>}
            </ul>
          </div>
        </CardContent>
      </Card>

      {(meta || debateT) && (
        <Card className="bg-transparent border-border/60">
          <CardHeader className="py-3">
            <CardTitle className="text-base">Meta verdict</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            {meta && (
              <>
                <div>
                  <span className="text-muted-foreground">Signal: </span>
                  <strong>{String(meta.signal)}</strong>
                </div>
                <div>
                  <span className="text-muted-foreground">Conviction: </span>
                  {String(meta.conviction_score)}
                </div>
                <div>
                  <span className="text-muted-foreground">Position size cap: </span>
                  {String(meta.position_size_pct)}%
                </div>
                <p className="leading-relaxed whitespace-pre-wrap">{String(meta.investment_thesis || '')}</p>
              </>
            )}
            {!meta && debateT && (
              <p className="text-muted-foreground">{String(debateT.meta_summary || '')}</p>
            )}
          </CardContent>
        </Card>
      )}

      <Accordion type="multiple" className="w-full">
        {agents.map((a) => (
          <AccordionItem value={a.id} key={a.id}>
            <AccordionTrigger className="text-xs py-2">{a.id} — reasoning</AccordionTrigger>
            <AccordionContent>
              {a.steps && (
                <ol className="list-decimal pl-4 space-y-1 text-xs text-muted-foreground">
                  {a.steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              )}
              {a.conviction && <p className="text-xs mt-2">{a.conviction}</p>}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
