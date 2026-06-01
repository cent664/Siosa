interface Props {
  timing: Record<string, number> | undefined;
}

export default function TimingRow({ timing }: Props) {
  if (!timing || Object.keys(timing).length === 0) return null;

  return (
    <div>
      <p className="section-label">Timing (ms)</p>
      <table className="compact-metrics">
        <tbody>
          <tr>
            {Object.entries(timing).map(([k, v]) => (
              <td key={k}>
                <b>{k}</b>
                <span className="val">{v}</span>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
