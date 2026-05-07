const cards = [
  {
    title: "Inventorypage Overview",
    detail: "Inventory workflow and APIs."
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Inventorypage() {
  return (
    <section className="card">
      <h2>Inventorypage</h2>
      <p>Inventory workflow and APIs.</p>
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
