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
                        food = food.strip()
                        qty_str = qty_str.strip()

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

冷蔵庫の中身（食材）及び自分のレパートリーのレシピを登録するアプリを開発したいです。自分のレパートリーに対して必要な食材は何が足りないのかを一目でわかるようにしたいです。言語はpythonでお願いします。それとコードの解説をお願いします。
足りない食材を確認する時に、今まで登録したレシピの中から選択できるようにしてください
一回レシピを登録したら保存されるされるようにしたいのですが、WEBアプリ化して、そうすることはできますか？
このコードはどこで実行すればよいですか？VScodeで実行は可能ですか
作動しました。
さらに一度登録した冷蔵庫の中身を削除できるようにしてください。
冷蔵庫の中身の数量管理を出来るようにしてください
elif action == "add_ingredient":　でsyntaxEror:invalid syntaxと表示されました
    if request.method == "POST":
        action = request.form.get("action")

    # 食材追加
    elif action == "add_ingredient":
        item = request.form.get("ingredient")
        qty = int(request.form.get("quantity"))

        if item in data["fridge"]:
            data["fridge"][item] += qty
        else:
            data["fridge"][item] = qty
        
    # 食材削除
    elif action == "delete_ingredient":
        item = request.form.get("delete_item")
        qty = int(request.form.get("delete_quantity"))

        if item in data["fridge"]:
            data["fridge"][item] -= qty
        
            if data["fridge"][item] <= 0:
                del data["fridge"][item]

    # レシピ追加
    elif action == "add_recipe":
        name = request.form.get("recipe_name")
        ingredients_raw = request.form.get("ingredients")

        # 例: 玉ねぎ:1,にんじん:2,肉:1
        ingredient_dict = {}
        for item in ingredients_raw.split(","):
            food, qty = item.split(":")
            ingredient_dict[food] = int(qty)

        data["recipes"][name] = ingredient_dict

    # 不足チェック
    elif action == "check":
        selected_recipe = request.form.get("recipe_select")

        recipe_ingredients = data["recipes"][selected_recipe]
        fridge = data["fridge"]

        missing = {}

        for item, required_qty in recipe_ingredients.items():
            fridge_qty = fridge.get(item, 0)

            if fridge_qty < required_qty:
                missing[item] = required_qty - fridge_qty

    save_data(data)
from flask import Flask, request, render_template_string
import json
import os


app = Flask(__name__)

DATA_FILE = "data.json"

# データ読み込み
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fridge": [], "recipes": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# データ保存
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# トップページ
@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message = ""
    missing = None
    selected_recipe = ""

if request.method == "POST":
    action = request.form.get("action")

    # 食材追加
    if action == "add_ingredient":
        item = request.form.get("ingredient")
        qty = int(request.form.get("quantity"))

        if item in data["fridge"]:
            data["fridge"][item] += qty
        else:
            data["fridge"][item] = qty

    # 食材削除
    elif action == "delete_ingredient":
        item = request.form.get("delete_item")
        qty = int(request.form.get("delete_quantity"))

        if item in data["fridge"]:
            data["fridge"][item] -= qty
        
            if data["fridge"][item] <= 0:
                del data["fridge"][item]

    # レシピ追加
    elif action == "add_recipe":
        name = request.form.get("recipe_name")
        ingredients_raw = request.form.get("ingredients")

        ingredient_dict = {}
        for item in ingredients_raw.split(","):
            food, qty = item.split(":")
            ingredient_dict[food] = int(qty)

        data["recipes"][name] = ingredient_dict

    # 不足チェック
    elif action == "check":
        selected_recipe = request.form.get("recipe_select")

        recipe_ingredients = data["recipes"][selected_recipe]
        fridge = data["fridge"]

        missing = {}

        for item, required_qty in recipe_ingredients.items():
            fridge_qty = fridge.get(item, 0)

            if fridge_qty < required_qty:
                missing[item] = required_qty - fridge_qty

    save_data(data)

    # HTML（簡易）
    html = """
    <h1>レシピ管理アプリ</h1>

    <h2>食材追加</h2>
    <form method="post">
        <input name="ingredient" placeholder="食材名">
        <input name="quantity" type="number" placeholder="数量">
        <button name="action" value="add_ingredient">追加</button>
    </form>

    <h2>食材削除</h2>
    <form method="post">
        <select name="delete_item">
            {% for item in fridge %}
            <option value="{{item}}">{{item}}</option>
            {% endfor %}
        </select>
        <input name="delete_quantity" type="number" placeholder="数量">
        <button name="action" value="delete_ingredient">削除</button>
    </form>

    <h2>レシピ追加</h2>
    <form method="post">
        <input name="recipe_name" placeholder="料理名"><br>
        <input name="ingredients" placeholder="玉ねぎ:1,にんじん:2,肉:1">
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
    % endfor %}
    </ul>
    <p>{{ fridge }}</p>
    """

    return render_template_string(
        html,
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe
    )

if __name__ == "__main__":
    app.run(debug=True)
    
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
と表示されました
さいとにサクセスするとAttributeErrorとなります
vscodeを再起動したら治りました
正確には方法②をしたうえでvscodeを再起動しました
食材削除する時に、数量を選択しないと削除できないようにしてください。
③メッセージ表示はどこに追加すればいいですか
②と③を追記する場所を教えてください。
from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fridge": {}, "recipes": {}}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 旧データ対応（list → dict）
    if isinstance(data["fridge"], list):
        new_fridge = {}
        for item in data["fridge"]:
            new_fridge[item] = 1
        data["fridge"] = new_fridge

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message=""
    missing = None
    selected_recipe = ""

    if request.method == "POST":
        action = request.form.get("action")

        # 食材追加
        if action == "add_ingredient":
            item = request.form.get("ingredient")
            qty = int(request.form.get("quantity"))

            if item in data["fridge"]:
                data["fridge"][item] += qty
            else:
                data["fridge"][item] = qty

        # 食材削除
        elif action == "delete_ingredient":
            item = request.form.get("delete_item")
            qty = int(request.form.get("delete_quantity"))
            
            # 未入力チェック
            if not qty_str:
                message = "削除数量を入力してください"
            else:
                try:
                    qty = int(qty_str)

                    if qty <= 0:
                        message = "1以上の数量を入力してください"

                    elif item in data["fridge"]:
                        data["fridge"][item] -= qty

                        if data["fridge"][item] <= 0:
                            del data["fridge"][item]

                except ValueError:
                    message = "数量は数字で入力してください"

            if item in data["fridge"]:
                data["fridge"][item] -= qty
                if data["fridge"][item] <= 0:
                    del data["fridge"][item]

        # レシピ追加
        elif action == "add_recipe":
            name = request.form.get("recipe_name")
            ingredients_raw = request.form.get("ingredients")

            ingredient_dict = {}
            for item in ingredients_raw.split(","):
                food, qty = item.split(":")
                ingredient_dict[food] = int(qty)

            data["recipes"][name] = ingredient_dict

        # 不足チェック
        elif action == "check":
            selected_recipe = request.form.get("recipe_select")

            recipe_ingredients = data["recipes"][selected_recipe]
            fridge = data["fridge"]

            missing = {}

            for item, required_qty in recipe_ingredients.items():
                fridge_qty = fridge.get(item, 0)

                if fridge_qty < required_qty:
                    missing[item] = required_qty - fridge_qty

        save_data(data)

    html = """
    <h1>レシピ管理アプリ</h1>
    
    {% if message %}
    <p style="color:red;">{{ message }}</p>
    {% endif %}

    <h2>食材追加</h2>
    <form method="post">
        <input name="ingredient" placeholder="食材名">
        <input name="quantity" type="number" placeholder="数量">
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
        <input name="ingredients" placeholder="玉ねぎ:1,にんじん:2,肉:1">
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
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fridge": {}, "recipes": {}}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 旧データ対応（list → dict）
    if isinstance(data["fridge"], list):
        new_fridge = {}
        for item in data["fridge"]:
            new_fridge[item] = 1
        data["fridge"] = new_fridge

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message=""
    missing = None
    selected_recipe = ""

    if request.method == "POST":
        action = request.form.get("action")

        # 食材追加
        if action == "add_ingredient":
            item = request.form.get("ingredient")
            qty = int(request.form.get("quantity"))

            if item in data["fridge"]:
                data["fridge"][item] += qty
            else:
                data["fridge"][item] = qty

        # 食材削除
        elif action == "delete_ingredient":
            item = request.form.get("delete_item")
            qty_str = request.form.get("delete_quantity")

            # 未入力チェック
            if not qty_str:
                message = "削除数量を入力してください"
            else:
                try:
                    qty = int(qty_str)

                    if qty <= 0:
                        message = "1以上の数量を入力してください"

                    elif item in data["fridge"]:
                        if data["fridge"][item] < qty:
                            message = "在庫より多く削除できません"
                        else:
                            data["fridge"][item] -= qty

                            if data["fridge"][item] == 0:
                                del data["fridge"][item]

                except ValueError:
                    message = "数量は数字で入力してください"

            if item in data["fridge"]:
                data["fridge"][item] -= qty
                if data["fridge"][item] <= 0:
                    del data["fridge"][item]

        # レシピ追加
        elif action == "add_recipe":
            name = request.form.get("recipe_name")
            ingredients_raw = request.form.get("ingredients")

            ingredient_dict = {}
            for item in ingredients_raw.split(","):
                food, qty = item.split(":")
                ingredient_dict[food] = int(qty)

            data["recipes"][name] = ingredient_dict

        # 不足チェック
        elif action == "check":
            selected_recipe = request.form.get("recipe_select")

            recipe_ingredients = data["recipes"][selected_recipe]
            fridge = data["fridge"]

            missing = {}

            for item, required_qty in recipe_ingredients.items():
                fridge_qty = fridge.get(item, 0)

                if fridge_qty < required_qty:
                    missing[item] = required_qty - fridge_qty

        save_data(data)

    html = """
    <h1>レシピ管理アプリ</h1>
    
    {% if message %}
    <p style="color:red;">{{ message }}</p>
    {% endif %}

    <h2>食材追加</h2>
    <form method="post">
        <input name="ingredient" placeholder="食材名">
        <input name="quantity" type="number" placeholder="数量">
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
        <input name="ingredients" placeholder="玉ねぎ:1,にんじん:2,肉:1">
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
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    app.run(debug=True)

ふそく食材の確認をするとエラーになります
対策を書く場所を教えてください。
from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fridge": {}, "recipes": {}}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 旧データ対応（list → dict）
    if isinstance(data["fridge"], list):
        new_fridge = {}
        for item in data["fridge"]:
            new_fridge[item] = 1
        data["fridge"] = new_fridge

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message=""
    missing = None
    selected_recipe = ""

    if request.method == "POST":
        action = request.form.get("action")

        # 食材追加
        if action == "add_ingredient":
            item = request.form.get("ingredient")
            qty = int(request.form.get("quantity"))

            if item in data["fridge"]:
                data["fridge"][item] += qty
            else:
                data["fridge"][item] = qty

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

                    elif item in data["fridge"]:
                        if data["fridge"][item] < qty:
                            message = "在庫より多く削除できません"
                        else:
                            data["fridge"][item] -= qty

                            if data["fridge"][item] == 0:
                                del data["fridge"][item]

                except ValueError:
                    message = "数量は数字で入力してください"

            if item in data["fridge"]:
                data["fridge"][item] -= qty
                if data["fridge"][item] <= 0:
                    del data["fridge"][item]

        # レシピ追加
        elif action == "add_recipe":
            name = request.form.get("recipe_name")
            ingredients_raw = request.form.get("ingredients")

            ingredient_dict = {}
            for item in ingredients_raw.split(","):
                food, qty = item.split(":")
                ingredient_dict[food] = int(qty)

            data["recipes"][name] = ingredient_dict

        # 不足チェック
        elif action == "check":
            selected_recipe = request.form.get("recipe_select")

            # レシピ存在チェック（ここが追加ポイント）
            if selected_recipe in data["recipes"]:
                recipe_ingredients = data["recipes"][selected_recipe]
                fridge = data["fridge"]

                missing = {}

                for item, required_qty in recipe_ingredients.items():
                    fridge_qty = fridge.get(item, 0)

                    if fridge_qty < required_qty:
                        missing[item] = required_qty - fridge_qty
            else:
                message = "レシピが見つかりません"

        save_data(data)

    html = """
    <h1>レシピ管理アプリ</h1>
    
    {% if message %}
    <p style="color:red;">{{ message }}</p>
    {% endif %}

    <h2>食材追加</h2>
    <form method="post">
        <input name="ingredient" placeholder="食材名">
        <input name="quantity" type="number" placeholder="数量">
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
        <input name="ingredients" placeholder="玉ねぎ:1,にんじん:2,肉:1">
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
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fridge": {}, "recipes": {}}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 旧データ対応（list → dict）
    if isinstance(data["fridge"], list):
        new_fridge = {}
        for item in data["fridge"]:
            new_fridge[item] = 1
        data["fridge"] = new_fridge

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message=""
    missing = None
    selected_recipe = ""

    if request.method == "POST":
        action = request.form.get("action")

        # 食材追加
        if action == "add_ingredient":
            item = request.form.get("ingredient")
            qty = int(request.form.get("quantity"))

            if item in data["fridge"]:
                data["fridge"][item] += qty
            else:
                data["fridge"][item] = qty

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

                    elif item in data["fridge"]:
                        if data["fridge"][item] < qty:
                            message = "在庫より多く削除できません"
                        else:
                            data["fridge"][item] -= qty

                            if data["fridge"][item] == 0:
                                del data["fridge"][item]

                except ValueError:
                    message = "数量は数字で入力してください"

            if item in data["fridge"]:
                data["fridge"][item] -= qty
                if data["fridge"][item] <= 0:
                    del data["fridge"][item]

        # レシピ追加
        elif action == "add_recipe":
            name = request.form.get("recipe_name")
            ingredients_raw = request.form.get("ingredients")

            ingredient_dict = {}
            for item in ingredients_raw.split(","):
                food, qty = item.split(":")
                ingredient_dict[food] = int(qty)

            data["recipes"][name] = ingredient_dict

        # 不足チェック
        elif action == "check":
            selected_recipe = request.form.get("recipe_select")

            # レシピ存在チェック（ここが追加ポイント）
            if selected_recipe in data["recipes"]:
                recipe_ingredients = data["recipes"][selected_recipe]
                fridge = data["fridge"]

                missing = {}

                for item, required_qty in recipe_ingredients.items():
                    fridge_qty = fridge.get(item, 0)

                    if fridge_qty < required_qty:
                        missing[item] = required_qty - fridge_qty
            else:
                message = "レシピが見つかりません"

        save_data(data)

    html = """
    <h1>レシピ管理アプリ</h1>
    
    {% if message %}
    <p style="color:red;">{{ message }}</p>
    {% endif %}

    <h2>食材追加</h2>
    <form method="post">
        <input name="ingredient" placeholder="食材名">
        <input name="quantity" type="number" placeholder="数量">
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
        <input name="ingredients" placeholder="玉ねぎ:1,にんじん:2,肉:1">
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
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fridge": {}, "recipes": {}}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 旧データ対応（list → dict）
    if isinstance(data["fridge"], list):
        new_fridge = {}
        for item in data["fridge"]:
            new_fridge[item] = 1
        data["fridge"] = new_fridge

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message=""
    missing = None
    selected_recipe = ""

    if request.method == "POST":
        action = request.form.get("action")

        # 食材追加
        if action == "add_ingredient":
            item = request.form.get("ingredient")
            qty = int(request.form.get("quantity"))

            if item in data["fridge"]:
                data["fridge"][item] += qty
            else:
                data["fridge"][item] = qty

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

                    elif item in data["fridge"]:
                        if data["fridge"][item] < qty:
                            message = "在庫より多く削除できません"
                        else:
                            data["fridge"][item] -= qty

                            if data["fridge"][item] == 0:
                                del data["fridge"][item]

                except ValueError:
                    message = "数量は数字で入力してください"
        

        # レシピ追加
        elif action == "add_recipe":
            name = request.form.get("recipe_name")
            ingredients_raw = request.form.get("ingredients")

            ingredient_dict = {}
            for item in ingredients_raw.split(","):
                food, qty = item.split(":")
                ingredient_dict[food] = int(qty)

            data["recipes"][name] = ingredient_dict

        # 不足チェック
        elif action == "check":
            selected_recipe = request.form.get("recipe_select")

            # レシピ存在チェック（ここが追加ポイント）
            if selected_recipe in data["recipes"]:
                recipe_ingredients = data["recipes"][selected_recipe]
                fridge = data["fridge"]

                missing = {}

                for item, required_qty in recipe_ingredients.items():
                    fridge_qty = fridge.get(item, 0)

                    if fridge_qty < required_qty:
                        missing[item] = required_qty - fridge_qty
            else:
                message = "レシピが見つかりません"

        save_data(data)

    html = """
    <h1>レシピ管理アプリ</h1>
    
    {% if message %}
    <p style="color:red;">{{ message }}</p>
    {% endif %}

    <h2>食材追加</h2>
    <form method="post">
        <input name="ingredient" placeholder="食材名">
        <input name="quantity" type="number" placeholder="数量">
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
        <input name="ingredients" placeholder="玉ねぎ:1,にんじん:2,肉:1">
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
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    app.run(debug=True)
AttributeErrorと表示されます
from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fridge": {}, "recipes": {}}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # fridge修正
    if isinstance(data["fridge"], list):
        new_fridge = {}
        for item in data["fridge"]:
            new_fridge[item] = 1
        data["fridge"] = new_fridge

    # 👇 これ追加（超重要）
    if isinstance(data["recipes"], list):
        data["recipes"] = {}

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message=""
    missing = None
    selected_recipe = ""

    if request.method == "POST":
        action = request.form.get("action")

        # 食材追加
        if action == "add_ingredient":
            item = request.form.get("ingredient")
            qty = int(request.form.get("quantity"))

            if item in data["fridge"]:
                data["fridge"][item] += qty
            else:
                data["fridge"][item] = qty

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

                    elif item in data["fridge"]:
                        if data["fridge"][item] < qty:
                            message = "在庫より多く削除できません"
                        else:
                            data["fridge"][item] -= qty

                            if data["fridge"][item] == 0:
                                del data["fridge"][item]

                except ValueError:
                    message = "数量は数字で入力してください"
        

        # レシピ追加
        elif action == "add_recipe":
            name = request.form.get("recipe_name")
            ingredients_raw = request.form.get("ingredients")

            ingredient_dict = {}
            for item in ingredients_raw.split(","):
                food, qty = item.split(":")
                ingredient_dict[food] = int(qty)

            data["recipes"][name] = ingredient_dict

        # 不足チェック
        elif action == "check":
            selected_recipe = request.form.get("recipe_select")

            # レシピ存在チェック（ここが追加ポイント）
            if selected_recipe in data["recipes"]:
                recipe_ingredients = data["recipes"][selected_recipe]
                fridge = data["fridge"]

                missing = {}

                for item, required_qty in recipe_ingredients.items():
                    fridge_qty = fridge.get(item, 0)

                    if fridge_qty < required_qty:
                        missing[item] = required_qty - fridge_qty
            else:
                message = "レシピが見つかりません"

        save_data(data)

    html = """
    <h1>レシピ管理アプリ</h1>
    
    {% if message %}
    <p style="color:red;">{{ message }}</p>
    {% endif %}

    <h2>食材追加</h2>
    <form method="post">
        <input name="ingredient" placeholder="食材名">
        <input name="quantity" type="number" placeholder="数量">
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
        <input name="ingredients" placeholder="玉ねぎ:1,にんじん:2,肉:1">
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
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    app.run(debug=True)
data.jsonの削除方法を具体的に教えてください。
エクスプローラーに「開いているエディター」「開いているフォルダーがありません」「アウトライン」「タイムライン」の項目しかありません
app.pyをデスクトップに保存しています。デスクトップを選択してもdata.jasonがありません
data.jsonを見つけました。デスクトップに移すのではだめなのですか？
DATA_FILE = "C:/Users/User/Desktop/recipe_app/data.json"にしました
数量を記入しないで食材を追加するとエラーni
レシピ追加するとエラーになります
このシステムをスマホでも使えるようにするのはハードルが高いですか？
できるなら外部のネットからもアクセスできるようにしたいのですが、一度同一wifiを経てからの方がやりやすいですか？
② Flaskを外部公開モードで起動を書く場所を教えてください。またhost="0.0.0.0"にIPアドレスを記入すればよいのでしょうか
スマホとPCを同じwifiに接続しましたが、スマホからはアクセスできません。
from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "C:/Users/User/Desktop/recipe_app/data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fridge": {}, "recipes": {}}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # fridgeを必ずdictにする（ここ強化）
    if not isinstance(data.get("fridge"), dict):
        data["fridge"] = {}

    # recipesも同様
    if not isinstance(data.get("recipes"), dict):
        data["recipes"] = {}

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message=""
    missing = None
    selected_recipe = ""

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
                        if item in data["fridge"]:
                            data["fridge"][item] += qty
                        else:
                            data["fridge"][item] = qty

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

                    elif item in data["fridge"]:
                        if data["fridge"][item] < qty:
                            message = "在庫より多く削除できません"
                        else:
                            data["fridge"][item] -= qty

                            if data["fridge"][item] == 0:
                                del data["fridge"][item]

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
                        data["recipes"][name] = ingredient_dict
                        message = "レシピを登録しました"

                except ValueError:
                    message = "数量は数字で入力してください"

        # 不足チェック
        elif action == "check":
            selected_recipe = request.form.get("recipe_select")

            # レシピ存在チェック（ここが追加ポイント）
            if selected_recipe in data["recipes"]:
                recipe_ingredients = data["recipes"][selected_recipe]
                fridge = data["fridge"]

                missing = {}

                for item, required_qty in recipe_ingredients.items():
                    fridge_qty = fridge.get(item, 0)

                    if fridge_qty < required_qty:
                        missing[item] = required_qty - fridge_qty
            else:
                message = "レシピが見つかりません"

        save_data(data)

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
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
ファイアーウォールでパブリックにチェックを入れるのはセキュリティ上問題ないのでしょうか
Pythonにプライベート許可を与えた結果スマホからもアクセスできました。
今後外部のネット環境からもアクセスできるようにする場合においても、同様にファイアウォールの設定をプライベート許可を与える必要があるのですか
Renderにデプロイする手順をゼロから一緒にやってください
①はvscodeでrequirements.txtという名称のファイルを作成し、中に
Flask
gunicorn
と記載すればいいのですか
お願いします。
ProcfileもVScodeで書くのが良いのですか？拡張子がないなら、メモ帳などで書いたあとに拡張子を消しても良いですか？
VScodeのエクスプローラーで確認した限りでは大丈夫だと思います。
OKです
git 未インストールです
⑤初期設定について教えてください。アカウント登録等が必要なのですか？またそのコードはターミナルに記載すれば良いのですか？
設定できました
⑧までやりましたが成功しているのかがよくわかりません。確認する方法を教えてください。
Git Hubのリポジトリにdata.jsonもあるのですが、これは無視してよいですか？
data.jasonをリポジトリから削除できました。他のファイルは見れます
renderもインストールが必要ですか
ログイン出来ました。New Web Serviceto
④ について、Create Web ServiceのボタンはなくDeploy Web Serviceはありますが、これを押せば良いか
URLでましたがNot Foundと表示されます
https://leng-zang-ku-nozhong-shen-guan-li-apuri.onrender.com/
from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "C:/Users/User/Desktop/recipe_app/data.json"
https://leng-zang-ku-nozhong-shen-guan-li-apuri.onrender.com/
更新しました
@app.route("/", methods=["GET", "POST"])
def index():
ありました。画面も表示されました。
データ消えないようにしたいです。それがSQLite化ですか？
SQLiteやりたい
import jason も消していいですか
③④⑤⑥は書き換えではなく追加ですか
食材追加の書き換えを詳しく解説してください
if qty <= 0:
　　message = "1以上の数量を入力してください" 
else:
　add_ingredient_db(item, qty)
で良いですか
from flask import Flask, request, render_template_string
import sqlite3
import os

app = Flask(__name__)

DB_FILE = "recipe.db"

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


@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    message=""
    missing = None
    selected_recipe = ""

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
                        message = "追加しました"                      

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

                    elif item in data["fridge"]:
                        if data["fridge"][item] < qty:
                            message = "在庫より多く削除できません"
                        else:
                            data["fridge"][item] -= qty

                            if data["fridge"][item] == 0:
                                del data["fridge"][item]

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
            if selected_recipe in data["recipes"]:
                recipe_ingredients = data["recipes"][selected_recipe]
                fridge = get_fridge()

                missing = {}

                for item, required_qty in recipe_ingredients.items():
                    fridge_qty = fridge.get(item, 0)

                    if fridge_qty < required_qty:
                        missing[item] = required_qty - fridge_qty
            else:
                message = "レシピが見つかりません"

       

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
        recipes=data["recipes"].keys(),
        fridge=data["fridge"],
        missing=missing,
        selected_recipe=selected_recipe,
        message=message
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
* Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.2.100:5000
Press CTRL+C to qui
スマホからアクセスはできましたが、食材やレシピを入力するとInternal server errorと表示されます
またInternal Server Errorとなります
127.0.0.1 - - [29/Apr/2026:10:46:34 +0000] "POST / HTTP/1.1" 500 265 "https://leng-zang-ku-nozhong-shen-guan-li-apuri.onrender.com/" "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.7.5 Mobile/15E148 Safari/604.1"
FileNotFoundError: [Errno 2] No such file or directory: 'C:/Users/User/Desktop/recipe_app/data.json'
from flask import Flask, request, render_template_string
import sqlite3
import os

app = Flask(__name__)
init_db()

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
                        message = "追加しました"                      

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
    
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
まだエラーがでます。食材を記入し数量を記載しないで追加をおすと「このフィールドに値を入力してください」と警告文はちゃんと表示されます。でも食材と数量を記入し追加を押すとエラーになります
[2026-04-29 10:53:04,650] ERROR in app: Exception on / [POST]
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1511, in wsgi_app
    response = self.full_dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 919, in full_dispatch_request
    rv = self.handle_user_exception(e)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 902, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "/opt/render/project/src/app.py", line 144, in index
    save_data(data)
    ~~~~~~~~~^^^^^^
  File "/opt/render/project/src/app.py", line 27, in save_data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
         ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: 'C:/Users/User/Desktop/recipe_app/data.json'
127.0.0.1 - - [29/Apr/2026:10:53:04 +0000] "POST / HTTP/1.1" 500 265 "https://leng-zang-ku-nozhong-shen-guan-li-apuri.onrender.com/" "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.7.5 Mobile/15E148 Safari/604.1"
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
                        message = "追加しました"                      

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
[2026-04-29 11:01:37,212] ERROR in app: Exception on / [POST]
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1511, in wsgi_app
    response = self.full_dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 919, in full_dispatch_request
    rv = self.handle_user_exception(e)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 902, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "/opt/render/project/src/app.py", line 144, in index
    save_data(data)
    ~~~~~~~~~^^^^^^
  File "/opt/render/project/src/app.py", line 27, in save_data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
         ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Menu
FileNotFoundError: [Errno 2] No such file or directory: 'C:/Users/User/Desktop/recipe_app/data.json'
127.0.0.1 - - [29/Apr/2026:11:01:37 +0000] "POST / HTTP/1.1" 500 265 "https://leng-zang-ku-nozhong-shen-guan-li-apuri.onrender.com/" "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.7.5 Mobile/15E148 Safari/604.1"
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