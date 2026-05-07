const cards = [
  {
    title: "Loanpage Overview",
    detail: "Loan and EMI workflow and APIs."
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Loanpage() {
  return (
    <section className="card">
      <h2>Loanpage</h2>
      <p>Loan and EMI workflow and APIs.</p>
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
