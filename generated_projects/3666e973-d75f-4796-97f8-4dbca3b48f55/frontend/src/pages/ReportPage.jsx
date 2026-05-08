const cards = [
  {
    title: "Reportpage Overview",
    detail: "Reports page and reporting workflow"
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Reportpage() {
  return (
    <section className="card">
      <h2>Reportpage</h2>
      <p>Reports page and reporting workflow</p>
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
