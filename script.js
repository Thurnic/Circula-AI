
"use strict";

// CIRCULA AI — GRUPO 01
// Interface integrada à API Flask

const $ = (id) => document.getElementById(id);

let analiseAtual = null;
let streamCamera = null;

// COMUNICAÇÃO COM O SERVIDOR

async function api(caminho, opcoes = {}) {
  let resposta;

  try {
    resposta = await fetch(caminho, {
      ...opcoes,
      headers: {
        "Content-Type": "application/json",
        ...(opcoes.headers || {})
      }
    });
  } catch {
    throw new Error(
      "Servidor indisponível. Execute python app.py."
    );
  }

  let dados;

  try {
    dados = await resposta.json();
  } catch {
    throw new Error("Resposta inválida do servidor.");
  }

  if (!resposta.ok) {
    throw new Error(
      dados.erro || "Não foi possível concluir a operação."
    );
  }

  return dados;
}

// SEGURANÇA NA EXIBIÇÃO DOS TEXTOS

function escapar(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[c]);
}

function numero(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    maximumFractionDigits: 2
  });
}

function erroNaTela(mensagem) {
  $("result").innerHTML = `
    <span class="pill danger">ERRO</span>
    <p>${escapar(mensagem)}</p>
  `;
}

// CONSULTAR EMBALAGEM CADASTRADA

async function consultarCodigo() {
  const codigo = $("code").value.trim().toUpperCase();

  if (!codigo) {
    erroNaTela("Informe o código da embalagem.");
    return;
  }

  try {
    const dados = await api(
      "/api/embalagem/" + encodeURIComponent(codigo)
    );

    $("material").value = dados.material;
    $("contamination").value = dados.contaminacao;
    $("description").value = dados.descricao;

    await analisarEmbalagem();
  } catch (erro) {
    erroNaTela(erro.message);
  }
}

// COLETAR INFORMAÇÕES DO FORMULÁRIO

function dadosFormulario() {
  return {
    codigo: $("code").value.trim() || "MANUAL",
    material: $("material").value,
    peso: Number($("weight").value),
    contaminacao: $("contamination").value,
    descricao: $("description").value.trim()
  };
}

// ANALISAR COM O CIRCULA CORE

async function analisarEmbalagem() {
  const dados = dadosFormulario();

  analiseAtual = null;
  $("save").disabled = true;

  if (!Number.isFinite(dados.peso) || dados.peso <= 0) {
    erroNaTela("Informe um peso válido.");
    return;
  }

  $("result").textContent = "Analisando embalagem...";

  try {
    const resultado = await api("/api/analisar", {
      method: "POST",
      body: JSON.stringify(dados)
    });

    analiseAtual = resultado;
    mostrarDiagnostico(resultado);

    $("save").disabled = false;
  } catch (erro) {
    erroNaTela(erro.message);
  }
}

// EXIBIR DIAGNÓSTICO

function mostrarDiagnostico(d) {
  const classe = d.nivel === "perigo"
    ? "danger"
    : d.nivel === "alerta"
      ? "warn"
      : "";

  const alertas = (d.alertas || [])
    .map(a => `<li>${escapar(a)}</li>`)
    .join("");

  $("result").innerHTML = `
    <span class="pill ${classe}">
      ${escapar(d.status)}
    </span>

    <h3>${escapar(d.material_nome)}</h3>

    <p><b>Código:</b> ${escapar(d.codigo)}</p>
    <p><b>Peso:</b> ${numero(d.peso)} kg</p>
    <p><b>Classificação:</b>
      ${escapar(d.classificacao)}
    </p>

    <p><b>Coletor:</b> ${escapar(d.coletor)}</p>

    <hr>

    <p><b>Segregação:</b>
      ${escapar(d.segregacao)}
    </p>

    <p><b>Armazenamento:</b>
      ${escapar(d.armazenamento)}
    </p>

    <p><b>Movimentação:</b>
      ${escapar(d.movimentacao)}
    </p>

    <p><b>Destinação:</b>
      ${escapar(d.destinacao)}
    </p>

    ${alertas ? `
      <h4>⚠️ Alertas</h4>
      <ul>${alertas}</ul>
    ` : ""}

    <p><small>${escapar(d.observacao)}</small></p>
  `;
}

// REGISTRAR DESCARTE NO SQLITE

async function registrarDescarte() {
  if (!analiseAtual) {
    alert("Analise uma embalagem primeiro.");
    return;
  }

  $("save").disabled = true;

  try {
    await api("/api/descartes", {
      method: "POST",
      body: JSON.stringify({
        codigo: analiseAtual.codigo,
        material: analiseAtual.material,
        peso: analiseAtual.peso,
        contaminacao: analiseAtual.contaminacao,
        descricao: analiseAtual.descricao
      })
    });

    analiseAtual = null;

    await atualizarDashboard();

    alert("✅ Descarte registrado com sucesso!");
  } catch (erro) {
    $("save").disabled = false;
    alert(erro.message);
  }
}

// ATUALIZAR DASHBOARD

async function atualizarDashboard() {
  try {
    const [resumo, registros] = await Promise.all([
      api("/api/dashboard"),
      api("/api/descartes")
    ]);

    $("total").textContent =
      numero(resumo.peso_total) + " kg";

    $("count").textContent = resumo.quantidade;
    $("alerts").textContent = resumo.alertas;

    if (!registros.length) {
      $("history").innerHTML = `
        <tr>
          <td colspan="5">Nenhum descarte registrado.</td>
        </tr>
      `;
      return;
    }

    $("history").innerHTML = registros.map((r) => `
      <tr>
        <td>${escapar(r.data)}</td>
        <td>${escapar(r.codigo)}</td>
        <td>${escapar(r.material)}</td>
        <td>${numero(r.peso)} kg</td>
        <td>${escapar(r.status)}</td>
      </tr>
    `).join("");
  } catch (erro) {
    console.error("Falha ao atualizar dashboard:", erro);
    erroNaTela(erro.message);
  }
}

// EXPORTAR HISTÓRICO PARA CSV

async function exportarCSV() {
  try {
    const registros = await api("/api/descartes");

    const linhas = [
      ["Data", "Código", "Material", "Peso (kg)", "Status"],
      ...registros.map(r => [
        r.data, r.codigo, r.material, r.peso, r.status
      ])
    ];

    const conteudo = "\ufeff" + linhas.map(linha =>
      linha.map(valor =>
        '"' + String(valor).replaceAll('"', '""') + '"'
      ).join(";")
    ).join("\r\n");

    const arquivo = new Blob([conteudo], {
      type: "text/csv;charset=utf-8"
    });

    const url = URL.createObjectURL(arquivo);
    const link = document.createElement("a");

    link.href = url;
    link.download = "circula_ai_relatorio.csv";
    link.click();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (erro) {
    alert(erro.message);
  }
}

// LIMPAR DADOS DE DEMONSTRAÇÃO

async function limparDados() {
  if (!confirm("Apagar todos os descartes cadastrados?")) {
    return;
  }

  try {
    await api("/api/descartes", {
      method: "DELETE"
    });

    analiseAtual = null;
    $("save").disabled = true;

    await atualizarDashboard();
  } catch (erro) {
    alert(erro.message);
  }
}

// LEITURA EXPERIMENTAL POR CÂMERA

function pararCamera() {
  if (streamCamera) {
    streamCamera.getTracks().forEach(t => t.stop());
  }

  streamCamera = null;
  $("scanner").style.display = "none";
}

async function lerQRCode() {
  if (!("BarcodeDetector" in window)) {
    alert(
      "Seu navegador não possui leitor nativo. " +
      "Digite o código manualmente."
    );
    return;
  }

  try {
    const formatos = await BarcodeDetector.getSupportedFormats();

    if (!formatos.includes("qr_code")) {
      throw new Error("QR Code não suportado.");
    }

    const detector = new BarcodeDetector({
      formats: ["qr_code"]
    });

    streamCamera = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" }
    });

    $("video").srcObject = streamCamera;
    $("scanner").style.display = "block";

    async function verificar() {
      if (!streamCamera) return;

      try {
        const codigos = await detector.detect($("video"));

        if (codigos.length) {
          let valor = codigos[0].rawValue;

          try {
            const endereco = new URL(valor);
            valor = endereco.searchParams.get("codigo") || valor;
          } catch {}

          $("code").value = valor.trim().toUpperCase();

          pararCamera();
          await consultarCodigo();
          return;
        }
      } catch {}

      if (streamCamera) {
        requestAnimationFrame(verificar);
      }
    }

    requestAnimationFrame(verificar);
  } catch (erro) {
    pararCamera();
    alert("Não foi possível acessar a câmera.");
  }
}

// INICIALIZAÇÃO

document.addEventListener("DOMContentLoaded", () => {
  $("lookup").addEventListener("click", consultarCodigo);
  $("analyze").addEventListener("click", analisarEmbalagem);
  $("save").addEventListener("click", registrarDescarte);

  $("export").addEventListener("click", exportarCSV);
  $("reset").addEventListener("click", limparDados);

  $("scan").addEventListener("click", lerQRCode);
  $("stop").addEventListener("click", pararCamera);

  document.querySelectorAll("[data-demo]").forEach(botao => {
    botao.addEventListener("click", () => {
      $("code").value = botao.dataset.demo;
      consultarCodigo();
    });
  });

  // Evita registrar uma análise antiga após
  // o funcionário modificar o formulário.
  ["code", "material", "weight",
   "contamination", "description"].forEach(id => {
    $(id).addEventListener("input", () => {
      analiseAtual = null;
      $("save").disabled = true;
    });
  });

  const codigoURL = new URLSearchParams(
    window.location.search
  ).get("codigo");

  if (codigoURL) {
    $("code").value = codigoURL;
    consultarCodigo();
  }

  atualizarDashboard();
});
