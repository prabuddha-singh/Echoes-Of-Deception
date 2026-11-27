using UnityEngine;
using System.Collections;
using UnityEngine.Networking;

public class BackendConnectionTest : MonoBehaviour
{
    private const string baseURL = "http://127.0.0.1:8000/api/";
    void Start()
    {
        StartCoroutine(CheckBackend());
    }

    private IEnumerator CheckBackend()
    {
        using(UnityWebRequest request = UnityWebRequest.Get(baseURL + "health/"))
        {
            yield return request.SendWebRequest();

            if(request.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("Backend connection succesful");
                Debug.Log(request.downloadHandler.text);
            }
            else
            {
                Debug.LogError("Connection failed "+request.error);
            }
        }
    }
}
