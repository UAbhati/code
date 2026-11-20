
class Solution {
    public:
        vector<vector<string>> accountsMerge(
            vector<vector<string>>& accounts
        ) {
            unordered_map<string, string> parent;
            unordered_map<string, int> rank;
            unordered_map<string, string> emailName;

            // Find with path compression
            function<string(string)> find = [&](string x) -> string {
                if (parent[x] != x) {
                    parent[x] = find(parent[x]);
                }
                return parent[x];
            };

            // Union by rank
            function<void(string, string)> unite =
                [&](string x, string y) {
                    string px = find(x);
                    string py = find(y);

                    if (px == py) return;

                    if (rank[px] < rank[py]) {
                        swap(px, py);
                    }

                    parent[py] = px;

                    if (rank[px] == rank[py]) {
                        rank[px]++;
                    }
                };

            // Step 1: Initialize emails and connect
            for (auto& account : accounts) {
                string name = account[0];
                string firstEmail = account[1];

                for (int i = 1; i < account.size(); i++) {
                    string email = account[i];

                    if (!parent.count(email)) {
                        parent[email] = email;
                        rank[email] = 0;
                    }

                    emailName[email] = name;

                    unite(firstEmail, email);
                }
            }

            // Step 2: Group emails by DSU root
            unordered_map<string, vector<string>> groups;

            for (unordered_map<string, string>::iterator it = parent.begin();
                 it != parent.end(); ++it) {

                string email = it->first;
                string root = find(email);

                groups[root].push_back(email);
            }

            // Step 3: Construct final answer
            vector<vector<string>> result;

            for (unordered_map<string, vector<string>>::iterator it = groups.begin();
                 it != groups.end(); ++it) {

                string root = it->first;
                vector<string>& emails = it->second;

                sort(emails.begin(), emails.end());

                vector<string> mergedAccount;

                mergedAccount.push_back(emailName[emails[0]]);

                for (int i = 0; i < emails.size(); i++) {
                    mergedAccount.push_back(emails[i]);
                }

                result.push_back(mergedAccount);
            }

            return result;
        }
    };
