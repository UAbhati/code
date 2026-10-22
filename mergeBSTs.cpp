
class Solution {
    public:
        TreeNode* canMerge(vector<TreeNode*>& trees) {
            unordered_map<int, TreeNode*> rootMap;
            unordered_set<int> childValues;

            // Map every tree root and collect all child values.
            for (TreeNode* tree : trees) {
                rootMap[tree->val] = tree;

                if (tree->left)
                    childValues.insert(tree->left->val);

                if (tree->right)
                    childValues.insert(tree->right->val);
            }

            // Find the root of the final BST.
            TreeNode* root = nullptr;

            for (TreeNode* tree : trees) {
                if (!childValues.count(tree->val)) {
                    root = tree;
                    break;
                }
            }

            if (!root) return nullptr;

            // The final root is already selected.
            rootMap.erase(root->val);

            function<bool(TreeNode*, long long, long long)> dfs =
                [&](TreeNode* node, long long low, long long high) -> bool {
                    if (!node) return true;

                    // Validate the global BST constraints.
                    if (node->val <= low || node->val >= high)
                        return false;

                    // Merge another tree when we reach a matching leaf.
                    if (!node->left && !node->right &&
                        rootMap.count(node->val)) {

                        TreeNode* tree = rootMap[node->val];

                        node->left = tree->left;
                        node->right = tree->right;

                        rootMap.erase(node->val);
                    }

                    return dfs(node->left, low, node->val) &&
                           dfs(node->right, node->val, high);
                };

            if (!dfs(root, LLONG_MIN, LLONG_MAX))
                return nullptr;

            // Every input tree must be used.
            if (!rootMap.empty())
                return nullptr;

            return root;
        }
    };
