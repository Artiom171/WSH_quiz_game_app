<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Ответы</title>

  <style>
    body {
      font-family: Arial;
      background: #f5f5f5;
      padding: 20px;
    }

    h2 {
      text-align: center;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
      border-radius: 10px;
      overflow: hidden;
    }

    th {
      background: #007bff;
      color: white;
      padding: 12px;
    }

    td {
      padding: 12px;
      border-bottom: 1px solid #ddd;
    }

    tr:hover {
      background: #f1f1f1;
    }
  </style>
</head>
<body>

<h2>Ответы игроков</h2>

<table>
  <thead>
    <tr>
      <th>Игрок</th>
      <th>Тур</th>
      <th>Вопрос</th>
      <th>Ответ</th>
    </tr>
  </thead>
  <tbody id="answersTable"></tbody>
</table>

<script>
async function loadAnswers() {
  const res = await fetch("http://192.168.1.18:8000/answers");
  const data = await res.json();

  const table = document.getElementById("answersTable");
  table.innerHTML = "";

  data.forEach(item => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${item.user_name}</td>
      <td>${item.round}</td>
      <td>${item.question_number}</td>
      <td>${item.answer_text}</td>
    `;

    table.appendChild(row);
  });
}

// автообновление
setInterval(loadAnswers, 2000);
loadAnswers();
</script>

</body>
</html>