const cards = [
  {
    title: "Transactionspage Overview",
    detail: "Transaction lookup workflow and APIs."
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Transactionspage() {
  return (
    <section className="card">
      <h2>Transactionspage</h2>
      <p>Transaction lookup workflow and APIs.</p>
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
