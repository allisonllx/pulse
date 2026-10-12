import { Scan } from '@/lib/scans';
import { conceptMatrix } from '@/lib/concepts';

export default function ConceptPatterns({scan,platform,onSelect}:{scan:Scan;platform:string;onSelect:(term:string,country:string)=>void}) {
  const rows=conceptMatrix(scan,platform);
  if(!scan.concept)return null;
  return <section className="concept-patterns" aria-label="Term patterns across markets">
    <span className="section-kicker">LOCAL VOCABULARY & VARIANTS</span><h4>How does each term surface?</h4>
    <p>The same terms in every market. Dots show unique links from sources that succeeded in all selected markets. Up to 20 dots per cell; the full count is shown. Select a cell to inspect its evidence.</p>
    <div className="concept-matrix-scroll"><table><thead><tr><th scope="col">Search term</th>{scan.countries.map(c=><th scope="col" key={c}>{c}</th>)}</tr></thead><tbody>{rows.map(row=><tr key={row.alias.term}><th scope="row">{row.alias.term}<small>{row.alias.kind} · {row.commonSources} comparable sources</small>{row.ambiguity&&<small>Includes fictional-name matches; inspect links.</small>}</th>{row.cells.map(cell=><td key={cell.country}><button disabled={!cell.available} onClick={()=>onSelect(row.alias.term,cell.country)} aria-label={`${row.alias.term} in ${cell.country}: ${cell.available?cell.count+' links':'coverage gap'}`} title={`${cell.successfulSources} successful source queries here`}><span className="term-dots" aria-hidden="true">{cell.available?Array.from({length:Math.min(cell.count,20)},(_,i)=><i key={i}/>):<span>?</span>}</span><small>{cell.available?`${cell.count} links`:'Coverage gap'}</small></button></td>)}</tr>)}</tbody></table></div>
    <div className="concept-question"><span className="section-kicker">EXPANSION QUESTION</span><p>{scan.concept.question}</p><small>Use the links and local variations to investigate this hypothesis. Search visibility alone does not establish demand or adoption.</small></div>
  </section>;
}
