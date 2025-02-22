import React from 'react'

interface ToggleSwitchProps {
  leftLabel: string
  rightLabel: string
  value: boolean
  onChange: (value: boolean) => void
}

const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  leftLabel,
  rightLabel,
  value,
  onChange,
}) => {
  return (
    <div className="flex items-center gap-2">
      <span className={`text-sm ${!value ? 'text-gray-900' : 'text-gray-500'}`}>
        {leftLabel}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent 
          transition-colors duration-200 ease-in-out focus:outline-none 
          ${value ? 'bg-gray-400' : 'bg-emerald-500'}
        `}
      >
        <span
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 
            transition duration-200 ease-in-out
            ${value ? 'translate-x-5' : 'translate-x-0'}
          `}
        />
      </button>
      <span className={`text-sm ${value ? 'text-gray-900' : 'text-gray-500'}`}>
        {rightLabel}
      </span>
    </div>
  )
}

export default ToggleSwitch
