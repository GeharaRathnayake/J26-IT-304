import React from 'react';
import { Card } from '../common/Card';
import { WeakTopicItem } from '../../types';
import './WeaknessTopicCard.css';

interface WeaknessTopicCardProps {
  topics: WeakTopicItem[];
}

export const WeaknessTopicCard: React.FC<WeaknessTopicCardProps> = ({ topics }) => {
  return (
    <Card className="weakness-card">
      <div className="weakness-card-header">
        <h3 className="weakness-card-title">Weakness topic area</h3>
        <p className="weakness-card-description">
          A topic is stored here as WEAK when the student needed 3 strategies to understand that one question.
        </p>
      </div>

      <div className="weakness-topics-list">
        {topics.length > 0 ? (
          topics.map((topic) => (
            <div key={topic.id} className="weakness-topic-row">
              <span className="weakness-topic-name">{topic.name}</span>
              <span className="weakness-topic-badge">{topic.status}</span>
            </div>
          ))
        ) : (
          <div className="weakness-topics-empty">
            <span>No weak topics identified yet. Keep up the great work!</span>
          </div>
        )}
      </div>
    </Card>
  );
};
