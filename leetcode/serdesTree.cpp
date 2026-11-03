/**
 * Definition for a binary tree node.
 * struct TreeNode {
 *     int val;
 *     TreeNode *left;
 *     TreeNode *right;
 *     TreeNode(int x) : val(x), left(NULL), right(NULL) {}
 * };
 */
 class Codec {
    public:

        // Serialize
        string serialize(TreeNode* root) {
            if (!root) return "null,";

            return to_string(root->val) + "," +
                   serialize(root->left) +
                   serialize(root->right);
        }

        // Deserialize
        TreeNode* build(vector<string>& nodes, int& i) {
            if (nodes[i] == "null") {
                i++;
                return nullptr;
            }

            TreeNode* root = new TreeNode(stoi(nodes[i]));
            i++;

            root->left = build(nodes, i);
            root->right = build(nodes, i);

            return root;
        }

        TreeNode* deserialize(string data) {
            vector<string> nodes;
            stringstream ss(data);
            string token;

            while (getline(ss, token, ',')) {
                if (!token.empty()) nodes.push_back(token);
            }

            int i = 0;
            return build(nodes, i);
        }
    };