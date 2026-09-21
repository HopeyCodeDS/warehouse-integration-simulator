import { Send } from 'lucide-react';

export function DispatchPanel({ onDispatch, isDispatching, message }) {
  return <section className="panel dispatch-panel">
    <div className="panel-heading"><div><span className="eyebrow">COMMAND CONSOLE</span><h2>Dispatch a mission</h2></div><Send size={18} className="panel-icon" /></div>
    <form onSubmit={onDispatch} className="dispatch-form">
      <label>Customer<input name="customer" defaultValue="Toyota" required /></label>
      <label>Destination<select name="dock" defaultValue="Dock-3"><option>Dock-1</option><option>Dock-2</option><option>Dock-3</option></select></label>
      <label>Product SKU<select name="sku" defaultValue="P100"><option value="P100">P100 / Engine Block</option><option value="P200">P200 / Transmission</option><option value="P300">P300 / Brake Pads</option></select></label>
      <label>Quantity<input name="quantity" type="number" min="1" defaultValue="1" required /></label>
      <button type="submit" disabled={isDispatching}><Send size={15} />{isDispatching ? 'DISPATCHING' : 'DISPATCH ORDER'}</button>
    </form>
    {message && <p className={`dispatch-message ${message.type}`}>{message.text}</p>}
  </section>;
}
