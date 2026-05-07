import { getProjectHealth } from "../services/api";

export default function HomePage() {
  const projectHealth = getProjectHealth();

  return (
    <section className="card">
      <h2>Starter Overview</h2>
      <p>This 100% runnable starter project is ready for your first feature slice.</p>
      <p>API health source: {projectHealth}</p>
    </section>
  );
}
