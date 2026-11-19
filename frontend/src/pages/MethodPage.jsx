import { Link } from 'react-router-dom';
import { useData } from '../hooks/useData';
import { PageTitle, ErrorBox } from '../components/UI';

export default function MethodPage() {
  const state = useData('/recommendations/evidence/');
  const data = state.data;
  const percent = (n) => (n * 100).toFixed(1) + '%';
  return <>
    <PageTitle eyebrow="HOW IT WORKS" title="Real data. Explainable discovery.">
      Find people to explore technology with, and understand each suggestion.
    </PageTitle>
    <div className="method-flow">
      {['Your technologies', 'K-Means groups', 'Random Forest preferences', 'Learning exchange'].map((label, i) => <div key={label}><span>{i + 1}</span><strong>{label}</strong></div>)}
    </div>
    <section className="card">
      <h2>What is the model actually learning?</h2>
      <p>The Random Forest predicts languages developers say they want to use, using real Stack Overflow survey responses. K-Means discovers groups of similar technology profiles.</p>
      <p>ConnectAI compares these preferences with people’s profiles. It also shows what you want to use that someone else has used, and the reverse direction. A discovery score is a ranking aid, not a friendship-success probability.</p>
      <a href="https://survey.stackoverflow.co/2024/methodology" target="_blank" rel="noreferrer">Original dataset and methodology ↗</a>
    </section>
    <ErrorBox message={state.error} retry={state.reload} />
    {state.loading && <p role="status">Loading measured results…</p>}
    {data && <>
      <div className="evidence-stats">
        <article className="card"><small>Original real responses</small><strong>{data.audit.raw_rows.toLocaleString()}</strong></article>
        <article className="card"><small>Held-out accuracy per language</small><strong>{percent(data.test.per_label_accuracy)}</strong></article>
        <article className="card"><small>Micro F1</small><strong>{data.test.f1_micro.toFixed(3)}</strong></article>
        <article className="card"><small>Probability RMSE</small><strong>{data.test.probability_rmse.toFixed(3)}</strong></article>
      </div>
      <section className="card">
        <h2>Read the results honestly</h2>
        <p>{data.test.correct.toLocaleString()} correct and {data.test.wrong.toLocaleString()} wrong decisions on unseen respondents. One decision means one person and one language. Many languages are not selected, so accuracy alone can look better than the model really is.</p>
        <div className="table-scroll"><table className="evidence-table"><thead><tr><th>Method</th><th>Micro F1</th><th>MSE</th><th>RMSE</th></tr></thead><tbody>
          {[['Random Forest', data.test], ['Training frequency baseline', data.baselines.training_prevalence], ['Continue current languages', data.baselines.continue_current_languages]].map(([label, row]) => <tr key={label}><td>{label}</td><td>{row.f1_micro.toFixed(3)}</td><td>{row.probability_mse.toFixed(3)}</td><td>{row.probability_rmse.toFixed(3)}</td></tr>)}
        </tbody></table></div>
        <p className="muted">MSE averages the squared error between a probability and the actual 0/1 response. RMSE is its square root. Lower error is better.</p>
      </section>
      <section className="card">
        <h2>Chosen using validation data</h2>
        <div className="parameter-tags">{Object.entries(data.selected_parameters).map(([key, value]) => <span key={key}>{key.replaceAll('_', ' ')}: <strong>{String(value)}</strong></span>)}</div>
        <p>K-Means: {data.clustering.selected_k} groups, selected by validation silhouette. We keep the final test data separate from parameter selection.</p>
      </section>
      <section className="card">
        <h2>What happens when answers are missing?</h2>
        <p>Unanswered technologies stay unknown. Missing coding years use the training-set median with a missing-value flag. Empty or unsupported technology profiles receive no ML score.</p>
        <div className="table-scroll"><table className="evidence-table"><thead><tr><th>Artificial fields hidden</th><th>Coverage</th><th>Abstained</th><th>F1 on supported profiles</th></tr></thead><tbody>{data.artificial_masking_stress_test.map(row => <tr key={row.artificial_field_mask_rate}><td>{percent(row.artificial_field_mask_rate)}</td><td>{percent(row.coverage)}</td><td>{row.abstained_rows}</td><td>{row.metrics_supported_only?.f1_micro.toFixed(3) ?? 'No predictions'}</td></tr>)}</tbody></table></div>
        <p className="muted">This stress test deliberately hides fields. It is separate from missing values found in the original survey.</p>
      </section>
      <section className="card"><h2>Limits of this experiment</h2><ul>{data.limitations.map(text => <li key={text}>{text}</li>)}</ul><p>Community activity suggestions use your separate interests. Project suggestions use technology coverage; neither is presented as a trained success model.</p></section>
    </>}
    <Link to="/profile">Update my technology profile →</Link>
  </>;
}
