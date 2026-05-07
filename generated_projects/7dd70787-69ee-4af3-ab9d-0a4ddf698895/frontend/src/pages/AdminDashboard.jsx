const cards = [
  {
    title: "Admindashboard Overview",
    detail: "Admin dashboard page"
  },
  {
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }
];

export default function Admindashboard() {
  return (
    <section className="card">
      <h2>Admindashboard</h2>
      <p>Admin dashboard page</p>
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
