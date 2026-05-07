const cards = [
  {
    title: "Dashboardpage Overview",
    detail: "Primary project-specific frontend page for the main user workflow."
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Dashboardpage() {
  return (
    <section className="card">
      <h2>Dashboardpage</h2>
      <p>Primary project-specific frontend page for the main user workflow.</p>
      <ul>
        {cards.map((card) => (
          <li key={card.title}>
            <strong>{card.title}</strong>: {card.detail}
          </li>
        ))}
      </ul>
    </section>
  );
}
