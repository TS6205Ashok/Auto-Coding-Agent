const cards = [
  {
    title: "Locationspage Overview",
    detail: "Branch and ATM location workflow and APIs."
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Locationspage() {
  return (
    <section className="card">
      <h2>Locationspage</h2>
      <p>Branch and ATM location workflow and APIs.</p>
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
