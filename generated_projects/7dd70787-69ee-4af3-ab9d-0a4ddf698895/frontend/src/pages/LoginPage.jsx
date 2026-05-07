const cards = [
  {
    title: "Loginpage Overview",
    detail: "Authentication workflow and APIs."
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Loginpage() {
  return (
    <section className="card">
      <h2>Loginpage</h2>
      <p>Authentication workflow and APIs.</p>
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
