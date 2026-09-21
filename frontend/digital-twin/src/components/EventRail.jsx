export function EventRail({ events, formatPayload }) {
  return (
    <section className="panel event-panel">
      <div className="panel-heading"><div><span className="eyebrow">SESSION TELEMETRY</span><h2>Event rail</h2></div><span className="session-badge">LIVE / {events.length}</span></div>
      <div className="event-list">
        {events.length === 0 && <div className="empty-state">Listening for warehouse events...</div>}
        {events.map((event) => <article className={`event-row ${event.severity}`} key={event.id}>
          <div className="event-meta"><span className="event-dot" /><time>{event.time.toLocaleTimeString()}</time><span>{event.topic}</span></div>
          <code>{formatPayload(event.payload)}</code>
        </article>)}
      </div>
    </section>
  );
}
