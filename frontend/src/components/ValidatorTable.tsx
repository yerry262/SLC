import type { Validator } from '../types'
import './ValidatorTable.css'

interface ValidatorTableProps {
  validators: Validator[]
}

function truncate(pubkey: string) {
  return `${pubkey.slice(0, 8)}…${pubkey.slice(-6)}`
}

export function ValidatorTable({ validators }: ValidatorTableProps) {
  return (
    <div className="validator-table">
      <h2 className="validator-table__title">Validators</h2>
      <table>
        <thead>
          <tr>
            <th scope="col" className="validator-table__status-col">
              status
            </th>
            <th scope="col">pubkey</th>
            <th scope="col">index</th>
            <th scope="col">balance</th>
            <th scope="col">days online</th>
          </tr>
        </thead>
        <tbody>
          {validators.map((v) => (
            <tr key={v.index}>
              <td>
                <span
                  className={`validator-table__dot validator-table__dot--${v.status}`}
                  title={v.status}
                />
              </td>
              <td className="validator-table__pubkey" title={v.pubkey}>
                {truncate(v.pubkey)}
              </td>
              <td>#{v.index}</td>
              <td>{v.status === 'exited' ? '—' : `${v.balanceEth.toFixed(4)} ETH`}</td>
              <td>{v.status === 'exited' ? '—' : v.daysOnline}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
