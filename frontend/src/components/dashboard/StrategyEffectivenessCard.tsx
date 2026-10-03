import React from 'react';
import { Card } from '../common/Card';
import { ProgressBar } from '../common/ProgressBar';
import { StrategyEffectivenessItem } from '../../types';
import './StrategyEffectivenessCard.css';

interface StrategyEffectivenessCardProps {
  strategies: StrategyEffectivenessItem[];
}

export const StrategyEffectivenessCard: React.FC<StrategyEffectivenessCardProps> = ({
  strategies,
}) => {
  return (
    <Card className="strategy-card">
      <div className="strategy-card-header">
        <h3 className="strategy-card-title">Observed Strategy Effectiveness</h3>
        <p className="strategy-card-description">
          Share of successful explanations per strategy. This is not model accuracy.
        </p>
      </div>

      <div className="strategy-bars-list">
        {strategies.map((item) => (
          <ProgressBar
            key={item.id}
            label={item.strategy}
            percentage={item.percentage}
          />
        ))}
      </div>
    </Card>
  );
};
