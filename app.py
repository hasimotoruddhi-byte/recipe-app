from flask import Flask, request, render_template_string
import sqlite3
import os

app = Flask(__name__)


DB_FILE = "/tmp/recipe.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # 食材テーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fridge (
        name TEXT PRIMARY KEY,
        quantity INTEGER
    )
    """)

    # レシピテーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        name TEXT,
        ingredient TEXT,
        quantity INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

#食材追加
def add_ingredient_db(item, qty):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT quantity FROM fridge WHERE name=?", (item,))
    row = cur.fetchone()

    if row:
        cur.execute("UPDATE fridge SET quantity = quantity + ? WHERE name=?", (qty, item))
    else:
        cur.execute("INSERT INTO fridge (name, quantity) VALUES (?, ?)", (item, qty))

    conn.commit()
    conn.close()

#食材取得
def get_fridge():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT name, quantity FROM fridge")
    rows = cur.fetchall()

    conn.close()

    return {name: qty for name, qty in rows}

#レシピ登録
def add_recipe_db(name, ingredient_dict):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    for food, qty in ingredient_dict.items():
        cur.execute(
            "INSERT INTO recipes (name, ingredient, quantity) VALUES (?, ?, ?)",
            (name, food, qty)
        )

    conn.commit()
    conn.close()

#レシピ取得
def get_recipes():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT name, ingredient, quantity FROM recipes")
    rows = cur.fetchall()

    conn.close()

    recipes = {}
    for name, ing, qty in rows:
        recipes.setdefault(name, {})[ing] = qty

    return recipes

#食材削除
def delete_ingredient_db(item, qty):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT quantity FROM fridge WHERE name=?", (item,))
    row = cur.fetchone()

    if row:
        if row[0] > qty:
            cur.execute("UPDATE fridge SET quantity = quantity - ? WHERE name=?", (qty, item))
        else:
            cur.execute("DELETE FROM fridge WHERE name=?", (item,))

    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def index():
    message=""
    missing = None
    selected_recipe = ""
    
    fridge = get_fridge()
    recipes = get_recipes()

    if request.method == "POST":
        action = request.form.get("action")

        # 食材追加
        if action == "add_ingredient":
            item = request.form.get("ingredient")
            qty_str = request.form.get("quantity")

            if not item or not qty_str:
                message = "食材名と数量を入力してください"
            else:
                try:
                    qty = int(qty_str)

                    if qty <= 0:
                        message = "1以上の数量を入力してください"
                    else:
                        add_ingredient_db(item, qty)
                        message = "食材を追加しました"

                except ValueError:
                    message = "数量は数字で入力してください"

        # 食材削除
        elif action == "delete_ingredient":
            item = request.form.get("delete_item")
            qty_str = request.form.get("delete_quantity")

            if not qty_str:
                message = "削除数量を入力してください"
            else:
                try:
                    qty = int(qty_str)

                    if qty <= 0:
                        message = "1以上の数量を入力してください"
                    else:
                        delete_ingredient_db(item, qty)
                        message = "削除しました"

                except ValueError:
                    message = "数量は数字で入力してください"
        

        # レシピ追加
        elif action == "add_recipe":
            name = request.form.get("recipe_name")
            ingredients_raw = request.form.get("ingredients")

            if not name or not ingredients_raw:
                message = "料理名と材料を入力してください"
            else:
                ingredient_dict = {}

                try:
                    for item in ingredients_raw.split(","):
                        if ":" not in item:
                            message = "材料は「食材:数量」の形式で入力してください"
                            break

                        food, qty_str = item.split(":")
                        qty = int(qty_str)

                        if qty <= 0:
                            message = "数量は1以上で入力してください"
                            break

                        ingredient_dict[food] = qty

                    else:
                        # 正常時のみ登録
                        add_recipe_db(name, ingredient_dict)
                        message = "レシピを登録しました"

                except ValueError:
                    message = "数量は数字で入力してください"

        # 不足チェック
        elif action == "check":
            selected_recipe = request.form.get("recipe_select")

            # レシピ存在チェック（ここが追加ポイント）
            if selected_recipe in recipes:
                recipe_ingredients = recipes[selected_recipe]
                fridge = get_fridge()

                missing = {}

                for item, required_qty in recipe_ingredients.items():
                    fridge_qty = fridge.get(item, 0)

                    if fridge_qty < required_qty:
                        missing[item] = required_qty - fridge_qty
            else:
                message = "レシピが見つかりません"
                
        fridge = get_fridge()
        recipes = get_recipes()

       

    html = """
    <h1>レシピ管理アプリ</h1>
    
    {% if message %}
    <p style="color:red;">{{ message }}</p>
    {% endif %}

    <h2>食材追加</h2>
    <form method="post">
        <input name="ingredient" placeholder="食材名">
        <input name="quantity" type="number" min="1" required placeholder="数量">
        <button name="action" value="add_ingredient">追加</button>
    </form>

    <h2>食材削除</h2>
    <form method="post">
        <select name="delete_item">
            {% for item in fridge %}
            <option value="{{item}}">{{item}}</option>
            {% endfor %}
        </select>

        <input name="delete_quantity" type="number" min="1" required placeholder="数量">

        <button name="action" value="delete_ingredient">削除</button>
    </form>

    <h2>レシピ追加</h2>
    <form method="post">
        <input name="recipe_name" placeholder="料理名"><br>
        <input name="ingredients" placeholder="例：玉ねぎ:1,にんじん:2,肉:1" required>
        <button name="action" value="add_recipe">登録</button>
    </form>

    <h2>不足食材チェック</h2>
    <form method="post">
        <select name="recipe_select">
            {% for r in recipes %}
            <option value="{{r}}">{{r}}</option>
            {% endfor %}
        </select>
        <button name="action" value="check">確認</button>
    </form>

    {% if missing is not none %}
        <h3>{{selected_recipe}} の不足食材</h3>
        {% if missing %}
            <p>{{ missing }}</p>
        {% else %}
            <p>作れます！</p>
        {% endif %}
    {% endif %}

    <h2>現在の食材</h2>
    <ul>
    {% for item, qty in fridge.items() %}
        <li>{{item}} : {{qty}}</li>
    {% endfor %}
    </ul>
    """

    return render_template_string(
        html,
        recipes=recipes.keys(),
        fridge=fridge,
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)