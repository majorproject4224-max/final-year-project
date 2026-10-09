const select = document.querySelector("#student");
const find = document.querySelector("#find");
const profile = document.querySelector("#profile");
const status = document.querySelector("#status");
const results = document.querySelector("#results");
let students = [];

async function get(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw Error(data.error || "Request failed");
  return data;
}

function profileText() {
  const student = students.find((item) => item.id === select.value);
  profile.textContent = student
    ? `${student.branch} | Year ${student.year} | Skills: ${student.skills} | Interests: ${student.interests}`
    : "";
}

function render(items) {
  const template = document.querySelector("#card");
  results.replaceChildren();
  items.forEach((item, index) => {
    const card = template.content.cloneNode(true);
    card.querySelector("i").textContent = `#${index + 1}`;
    card.querySelector("h3").textContent = item.name;
    card.querySelector(".detail").textContent = `${item.branch} | Year ${item.year} | ${item.experience} | ${item.city}`;
    card.querySelector(".project").textContent = `Preferred: ${item.project}`;
    card.querySelector("strong b").textContent = `${item.score}%`;
    item.reasons.forEach((reason) => {
      const line = document.createElement("li");
      line.textContent = reason;
      card.querySelector("ul").append(line);
    });
    results.append(card);
  });
}

async function recommend() {
  find.disabled = true;
  status.textContent = "Ranking profiles...";
  try {
    const data = await get(`/api/recommendations?student_id=${encodeURIComponent(select.value)}`);
    render(data.items);
    status.textContent = "Top 8 ranked matches";
  } catch (error) {
    status.textContent = error.message;
  } finally {
    find.disabled = false;
  }
}

async function initialize() {
  try {
    const [studentData, metrics] = await Promise.all([get("/api/students"), get("/api/metrics")]);
    students = studentData.students;
    students.forEach((student) => {
      select.add(new Option(`${student.name} - ${student.branch}, Year ${student.year}`, student.id));
    });
    select.value = "U0002";
    document.querySelector("#accuracy").textContent = `${(metrics.accuracy * 100).toFixed(0)}%`;
    document.querySelector("#f1").textContent = `${(metrics.compatible_f1 * 100).toFixed(1)}%`;
    document.querySelector("#rows").textContent = `${metrics.test_rows} / ${metrics.dataset_rows}`;
    profileText();
    recommend();
  } catch (error) {
    status.textContent = error.message;
  }
}

select.addEventListener("change", profileText);
find.addEventListener("click", recommend);
initialize();
