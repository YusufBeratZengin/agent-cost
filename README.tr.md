# agent-cost

[![CI](https://github.com/YusufBeratZengin/agent-cost/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/agent-cost/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/agent-cost)](https://pypi.org/project/agent-cost/) [![License: MIT](https://img.shields.io/github/license/YusufBeratZengin/agent-cost)](LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml) ![Dependencies: 0](https://img.shields.io/badge/dependencies-0-brightgreen.svg)

[English](README.md) | Türkçe

Yapay zekâ kodlama ajanlarının yerel oturum kayıtlarını gün, oturum, proje veya model bazında token kullanımı ve tahmini maliyet raporuna çevirir.

Zaten diskte duran dosyaları okur, ağa hiç bağlanmaz ve hiçbir bağımlılığı yoktur; kayıtlarınız bilgisayarınızdan çıkmaz.

```bash
pip install agent-cost
agent-cost examples/sessions examples/openai --prices examples/prices.toml
```

> Henüz PyPI'da yoksa depoyu klonlayıp `pip install .` kullanın. `pip install agent-cost` satırı ilk sürümden sonra çalışır.

![agent-cost çıktısı](docs/demo.svg)

## Demo

[`examples/`](examples) içindeki sentetik kayıtlarda gerçek çıktı:

```text
$ agent-cost examples/sessions examples/openai --prices examples/prices.toml
day         requests   input  output  cache_read  cache_write  cost (USD)
----------  --------  ------  ------  ----------  -----------  ----------
2026-03-02         3   2,604   2,890      13,096       10,200        0.09
2026-03-03         2   1,600   3,700      15,000        9,500        0.33
2026-03-04         3   4,500   2,800      21,000          800        0.04
2026-03-05         2   2,756   4,110      14,144        2,000        0.32
----------  --------  ------  ------  ----------  -----------  ----------
TOTAL             10  11,460  13,500      63,240       22,500        0.79
```

Birden çok boyuta göre grupla, tarihe göre süz:

```text
$ agent-cost examples/sessions --by project,model --since 2026-03-03 --prices examples/prices.toml
project     model                 requests  input  output  cache_read  cache_write  cost (USD)
----------  --------------------  --------  -----  ------  ----------  -----------  ----------
-demo-blog  claude-opus-demo-1           1  1,500   3,200       8,000        2,000        0.31
-demo-shop  claude-opus-demo-1           1    900   2,600      15,000        3,000        0.29
-demo-blog  claude-sonnet-demo-1         1    700   1,100           0        6,500        0.04
-demo-shop  claude-sonnet-demo-1         1    500   1,900      21,000          800        0.04
-demo-shop  claude-haiku-demo-1          1  2,200     600           0            0      0.0052
----------  --------------------  --------  -----  ------  ----------  -----------  ----------
TOTAL                                    5  5,800   9,400      44,000       12,300        0.69
```

## Önemli: fiyatları kendiniz doğrulayın

Maliyet sütunu bir **tahmindir**. Yerleşik fiyat tablosunda yalnızca **örnek değerler** vardır; yanlış ya da eski olabilirler, üstelik planınız, bölgeniz veya sözleşmeniz farklı fiyat getirebilir. Her zaman `--prices` ile kendi tablonuzu verin. Yerleşik tablo kullanılırsa araç bunu stderr'e yazar. Abonelik planlarında (sabit aylık ücret) token başına maliyet yoktur; sayıları "bu kullanım API fiyatlarıyla ne tutardı" diye okuyun.

## Kurulum

```bash
pip install agent-cost        # ilk sürümden sonra
pip install .                 # klonlanmış depodan
```

Python 3.10 veya üstü. Çalışma zamanı bağımlılığı yok.

## Kullanım

```bash
agent-cost YOL [YOL ...] [seçenekler]
```

`YOL` bir kayıt dosyası ya da klasördür (klasör içinde `*.jsonl` ve `*.ndjson` dosyaları özyinelemeli aranır).

| Seçenek | Anlamı |
|---|---|
| `-r, --reader` | `auto` (varsayılan, her satırda tüm okuyucuları dener), `claude-code`, `openai` |
| `-b, --by` | Virgülle ayrılmış gruplama: `day`, `session`, `project`, `model`. Varsayılan `day` |
| `-p, --prices DOSYA` | Fiyat tablosu (TOML veya JSON). Aşağıya bakın |
| `-f, --format` | `table` (varsayılan), `csv`, `json` |
| `--since`, `--until` | `YYYY-MM-DD`, UTC, ikisi de dahil. Tarih süzgeci varken zaman damgası olmayan kayıtlar atılır |
| `--project`, `--model` | Proje ya da model adı bu metni içeren satırlar kalır (büyük/küçük harf fark etmez) |
| `--print-default-prices` | Yerleşik örnek tabloyu TOML olarak yazdırır (kendi tablonuz için başlangıç) |

Çıkış kodları: `0` başarılı, `2` hatalı girdi (geçersiz tarih, olmayan yol, bozuk fiyat dosyası).

### Fiyat tablosu

Fiyatlar **1.000.000 token** başınadır. Model adı önce birebir, olmazsa adın başında geçen en uzun anahtarla, o da olmazsa adın içinde geçen en uzun anahtarla eşleşir. Yani `claude-sonnet` anahtarı tüm `claude-sonnet-*` kimliklerini kapsar. Eşleşmeyen modeller sayılır ama `*` ile işaretlenir ve maliyete katılmaz.

```toml
currency = "USD"

[models."claude-sonnet"]
input = 3.0
output = 15.0
cache_read = 0.3
cache_write = 3.75
```

Aynı yapı JSON olarak da olur: `{"models": {"claude-sonnet": {"input": 3.0, "output": 15.0}}}`. Eksik anahtarlar `0` sayılır.

### Desteklenen kayıt biçimleri

- **claude-code**: Claude Code proje oturumları (`projects/<klasör>/<oturum>.jsonl`). `message.usage` alanlarını (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) okur. Proje, taradığınız yolun altındaki ilk klasördür. Aynı mesaj ve istek kimliğiyle birden çok kez yazılmış (akış) mesajlar bir kez sayılır.
- **openai**: `usage` nesnesi taşıyan her JSONL satırı; nesne `response` ya da `body` içinde de olabilir. `prompt_tokens` / `completion_tokens` ve `input_tokens` / `output_tokens` anlaşılır. OpenAI önbellekteki token'ları (`cached_tokens`) prompt toplamının içinde bildirir; bu yüzden girdiden düşülüp önbellek okumasına yazılır.

Başka bir biçim eklemek küçük bir okuyucu sınıfı yazmak demektir; bkz. [CONTRIBUTING.md](CONTRIBUTING.md).

### Kütüphane

```python
from pathlib import Path
from agent_cost import build_report, load_prices, read_records

records = read_records([Path("examples/sessions")])
rows, total = build_report(records, load_prices(Path("examples/prices.toml")), ["model"])
print(total.total_tokens, round(total.cost, 4))
```

## Örnekler

[`examples/`](examples) tamamen sentetik kayıtlar (sahte projeler, sahte içerik) ve örnek bir fiyat tablosu içerir. Bu belgedeki her komut bunlar üzerinde çalışır.

## Nasıl çalışır

1. Yollar gezilir, her JSONL satırı çözülür (bozuk satırlar atlanır).
2. Her okuyucu satırı bir `Record`'a (zaman, oturum, proje, model, dört token sayısı) çevirir ya da yok sayar.
3. Kayıtlar süzülür, fiyatlanır ve gruplanır. Günler UTC'dir.

## Sınırlar ve gizlilik

- Maliyetler tahmindir; yukarıdaki uyarıya bakın. Kayıttaki token sayılarına olduğu gibi güvenilir.
- Düşünme ya da araç token'ları, ancak ajan bunları kayıttaki kullanıma kattıysa sayılır.
- Her şey yerelde çalışır. Kayıtlar özel istemler ve yollar içerebilir; agent-cost mesaj içeriğini asla yazdırmaz, yalnızca sayıları ve proje, oturum, model adlarını gösterir.

## Geliştirme

```bash
python -m pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy
pytest
python scripts/make-demo.py   # docs/demo.svg dosyasını yeniden üretir
```

Testler yalnızca sentetik veri kullanır.

## Katkı

Bkz. [CONTRIBUTING.md](CONTRIBUTING.md). Lütfen [Davranış Kuralları](CODE_OF_CONDUCT.md)'na uyun. Güvenlik açıklarını [SECURITY.md](SECURITY.md)'deki gibi bildirin.

## Lisans

[MIT](LICENSE)
