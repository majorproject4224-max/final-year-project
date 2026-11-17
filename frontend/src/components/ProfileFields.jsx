export const domains = ['AI / ML', 'Data Science', 'Web Development', 'Mobile Development', 'Backend Development', 'Cybersecurity', 'Cloud / DevOps', 'Other'];
export const experienceLevels = ['Beginner', 'Intermediate', 'Advanced'];
export function SelectField({ label, name, value, onChange, options, required = true }) {
  return <label>{label}<select name={name} value={value} onChange={onChange} required={required}><option value="">Choose…</option>{options.map(option => <option key={option}>{option}</option>)}</select></label>;
}
export const splitTags = value => value.split(',').map(v => v.trim()).filter(Boolean);
