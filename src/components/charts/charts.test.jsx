import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import BarChart from './BarChart';
import LineChart from './LineChart';
import StatCard from './StatCard';
import { formatoMoneda } from '../../utils/formato';

afterEach(() => {
  cleanup();
});

const serie = [
  { etiqueta: '2026-09-19', valor: 120000 },
  { etiqueta: '2026-09-20', valor: 340000 },
  { etiqueta: '2026-09-21', valor: 80000 },
];

describe('Gráficos del dashboard', () => {
  it('el gráfico de barras dibuja una barra por periodo', () => {
    const { container } = render(<BarChart title="Monto vendido" data={serie} formatValue={formatoMoneda} />);

    expect(container.querySelectorAll('rect')).toHaveLength(serie.length);
    expect(screen.getByText('2026-09-20')).not.toBeNull();
  });

  it('el gráfico lineal traza la serie y marca cada punto', () => {
    const { container } = render(<LineChart title="Ventas por periodo" data={serie} />);

    expect(container.querySelectorAll('circle')).toHaveLength(serie.length);
    expect(container.querySelector('path[stroke="#38bdf8"]')).not.toBeNull();
  });

  it('los gráficos avisan cuando no hay datos para los filtros', () => {
    render(<BarChart title="Monto vendido" data={[]} />);

    expect(screen.getByText(/sin datos para los filtros seleccionados/i)).not.toBeNull();
  });

  it('la Card de indicador formatea el valor como moneda', () => {
    render(<StatCard titulo="Total facturado" valor={1250000} formato="moneda" />);

    expect(screen.getByText('Total facturado')).not.toBeNull();
    expect(screen.getByText(/1\.250\.000/)).not.toBeNull();
  });
});
