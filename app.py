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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)