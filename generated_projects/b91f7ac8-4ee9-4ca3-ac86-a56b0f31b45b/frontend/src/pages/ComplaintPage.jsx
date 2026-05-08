const cards = [
  {
    title: "Complaintpage Overview",
    detail: "Complaint tracking workflow and APIs."
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Complaintpage() {
  return (
    <section className="card">
      <h2>Complaintpage</h2>
      <p>Complaint tracking workflow and APIs.</p>
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
