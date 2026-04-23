interface FollowUpChipsProps {
  followups: string[];
  onPick: (question: string) => void;
}

export function FollowUpChips({ followups, onPick }: FollowUpChipsProps) {
  if (!followups || followups.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-gray-100">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
        Suggested follow-ups
      </p>
      <div className="flex flex-wrap gap-2">
        {followups.map((q, idx) => (
          <button
            key={idx}
            onClick={() => onPick(q)}
            className="text-sm text-left bg-white border border-gray-200 rounded-full px-3 py-1.5 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
